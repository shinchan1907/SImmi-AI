import asyncio
import yaml
import sys
import time
import os
from pathlib import Path
from rich.console import Console
from rich.status import Status
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import httpx

from core.schemas import SimmiConfig
from core.agent import SimmiAgent
from core.logger import setup_logging, get_logger
from integrations.telegram import TelegramInterface
from integrations.whatsapp import WhatsAppInterface
from scheduler.manager import TaskScheduler

# Initialize structured logging
setup_logging()
logger = get_logger("main")
console = Console()

class Watchdog:
    def __init__(self, config: SimmiConfig, telegram=None, whatsapp=None, scheduler=None):
        self.config = config
        self.telegram = telegram
        self.whatsapp = whatsapp
        self.scheduler = scheduler

    async def check_health(self):
        """Continuously check system health and log events."""
        while True:
            try:
                # 1. Check Database
                engine = create_async_engine(self.config.database.url)
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                
                # 2. Check Redis
                from redis import Redis
                r = Redis.from_url(self.config.database.redis_url)
                r.ping()

                # 3. Check WhatsApp Bridge if enabled
                if self.config.whatsapp.enabled:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get("http://localhost:3000/status", timeout=2)
                        if resp.status_code != 200:
                            logger.error("watchdog_whatsapp_failure", status=resp.status_code)
                            # If bridge is dead, exit to let supervisor restart everything
                            sys.exit(1)

                # 4. Check Scheduler
                if self.scheduler and not self.scheduler.scheduler.running:
                    logger.error("watchdog_scheduler_not_running")
                    sys.exit(1)

            except Exception as e:
                logger.critical("watchdog_health_failure", error=str(e))
                # Critical failure detected - exit process to trigger supervisor restart
                sys.exit(1)
            
            await asyncio.sleep(60) # Check every minute

def cleanup_audio_files():
    """Deletes audio files older than 30 minutes."""
    path = "storage/audio"
    if not os.path.exists(path): return
    now = time.time()
    for f in os.listdir(path):
        f_path = os.path.join(path, f)
        if os.path.isfile(f_path) and os.stat(f_path).st_mtime < now - 30 * 60:
            os.remove(f_path)

async def check_database_health(url: str):
    """Checks if the database is accessible before booting."""
    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "Connected"
    except Exception as e:
        return False, str(e)

async def bootstrap():
    """Bootstraps the Simmi Agent services with animated progress."""
    console.print("\n[bold cyan]🚀 Simmi Agent Production Boot[/bold cyan]\n")
    
    with Status("[bold white]System Initialization[/bold white]", console=console, spinner="dots") as status:
        # 1. Loading Configuration
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            console.print("❌ [red]Configuration not found.[/red]")
            return
        
        with open(config_path, "r") as f:
            config = SimmiConfig(**yaml.safe_load(f))

        # 2. Connecting to Database
        db_ok, db_msg = await check_database_health(config.database.url)
        if not db_ok:
            console.print(f"❌ [red]Database Error:[/red] {db_msg}")
            return

        # 3. Initializing Memory System
        agent = SimmiAgent(config)
        await agent.memory.init_db()

        # 4. Starting Scheduler
        scheduler = TaskScheduler(config.database.url)
        scheduler.scheduler.add_job(cleanup_audio_files, 'interval', minutes=30)
        scheduler.start()

        # 5. Starting Interfaces
        # Telegram
        telegram_bot = TelegramInterface(config, agent)
        await telegram_bot.start()

        # WhatsApp (Baileys)
        whatsapp_bot = None
        if config.whatsapp.enabled:
            whatsapp_bot = WhatsAppInterface(config, agent)
            await whatsapp_bot.start()

        status.stop()
        
        # PART 10 STARTUP DISPLAY
        console.print(f"[bold green]Simmi Agent Running[/bold green]")
        console.print(f"Telegram: [green]connected[/green]")
        console.print(f"WhatsApp: [green]{'connected' if config.whatsapp.enabled else 'disabled'}[/green]")
        console.print(f"Voice: [green]{'ready' if config.voice.enabled else 'off'}[/green]")
        console.print(f"Memory: [green]ready (pgvector)[/green]")
        console.print("")
        
        # Start Watchdog
        watchdog = Watchdog(config, telegram_bot, whatsapp_bot, scheduler)
        await watchdog.check_health()

if __name__ == "__main__":
    try:
        asyncio.run(bootstrap())
    except KeyboardInterrupt:
        logger.info("system_shutdown_initiated")
    except SystemExit:
        logger.info("system_exit_triggered_by_watchdog")
    except Exception as e:
        logger.critical("system_crash", error=str(e))
        sys.exit(1)
