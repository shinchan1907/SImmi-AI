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

from core.schemas import SimmiConfig
from core.agent import SimmiAgent
from core.logger import setup_logging, get_logger
from integrations.telegram import TelegramInterface
from scheduler.manager import TaskScheduler

# Initialize structured logging
setup_logging()
logger = get_logger("main")
console = Console()

def cleanup_audio_files():
    """Deletes audio files older than 30 minutes."""
    path = "storage/audio"
    if not os.path.exists(path): return
    now = time.time()
    for f in os.listdir(path):
        f_path = os.path.join(path, f)
        if os.stat(f_path).st_mtime < now - 30 * 60:
            if os.path.isfile(f_path):
                os.remove(f_path)

async def check_database_health(url: str):
    """Checks if the database is accessible before booting."""
    try:
        engine = create_async_engine(url)
        # Try a simple connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "Connected"
    except Exception as e:
        error_msg = str(e)
        if "password authentication failed" in error_msg:
            return False, "Authentication Failed: Please check your database password in config/config.yaml"
        elif "connection refused" in error_msg:
            return False, "Connection Refused: Is PostgreSQL running on the specified host/port?"
        return False, f"Error: {error_msg}"

async def bootstrap():
    """Bootstraps the Simmi Agent services with animated progress."""
    console.print("\n[bold cyan]🚀 Simmi Agent Boot Sequence[/bold cyan]\n")
    
    with Status("[bold white]System Boot[/bold white]", console=console, spinner="dots") as status:
        # 1. Loading Configuration
        status.update("[bold white]Loading Configuration...[/bold white]")
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            logger.error("config_not_found", path=str(config_path))
            console.print("❌ [red]Configuration not found.[/red] Please run 'simmi init' first.")
            return
        
        try:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f)
                config = SimmiConfig(**config_dict)
            logger.info("configuration_loaded")
        except Exception as e:
            logger.error("config_parse_failed", error=str(e))
            console.print(f"❌ [red]Failed to parse configuration:[/red] {str(e)}")
            return

        # 2. Connecting to Database
        status.update("[bold white]Connecting to Database...[/bold white]")
        db_ok, db_msg = await check_database_health(config.database.url)
        if not db_ok:
            logger.error("database_health_check_failed", message=db_msg)
            console.print(f"❌ [red]Database Error:[/red] {db_msg}")
            console.print("\n💡 [yellow]Corrective Action:[/yellow] Ensure PostgreSQL is running and credentials in [bold]config/config.yaml[/bold] are correct.")
            return
        logger.info("database_connection_established")

        # 3. Initializing Memory System
        status.update("[bold white]Initializing Memory System...[/bold white]")
        agent = SimmiAgent(config)
        await agent.memory.init_db()
        logger.info("memory_system_initialized")

        # 4. Starting Scheduler
        status.update("[bold white]Starting Scheduler...[/bold white]")
        scheduler = TaskScheduler(config.database.url)
        scheduler.scheduler.add_job(cleanup_audio_files, 'interval', minutes=30)
        scheduler.start()
        logger.info("scheduler_started")

        # 5. Starting Telegram Bot
        status.update("[bold white]Starting Telegram Bot...[/bold white]")
        telegram_bot = TelegramInterface(config, agent)
        await telegram_bot.start()
        logger.info("telegram_bot_initialized")

        status.stop()
        console.print(f"✅ [bold green]System Fully Operational![/bold green]")
        console.print(f"🤖 [cyan]{config.personality.name}[/cyan] is now listening on Telegram.\n")
        
        # Keep the loop running
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(bootstrap())
    except KeyboardInterrupt:
        logger.info("system_shutdown_initiated")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.critical("system_crash", error=str(e))
