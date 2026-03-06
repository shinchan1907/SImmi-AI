import os
import sys
import time
import subprocess
import signal
import asyncio
from pathlib import Path
from core.logger import get_logger, setup_logging
from core.schemas import SimmiConfig
import yaml
from integrations.telegram import TelegramInterface
from core.agent import SimmiAgent

setup_logging()
logger = get_logger("supervisor")

# Path to store the PID
PID_FILE = Path("temp/simmi.pid")

class SimmiSupervisor:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.process = None
        self.config = self._load_config()
        self.agent = None
        self.telegram = None

    def _load_config(self):
        if not self.config_path.exists():
            return None
        with open(self.config_path, "r") as f:
            return SimmiConfig(**yaml.safe_load(f))

    async def _init_notify_channel(self):
        """Initialize a minimal telegram client for notifications."""
        if not self.config:
            return
        self.agent = SimmiAgent(self.config)
        self.telegram = TelegramInterface(self.config, self.agent)
        # We don't start the full polling here, just for sending alerts if possible
        # Or better, just a helper to send direct message

    async def notify_owner(self, message: str):
        """Send a message to the owner via Telegram."""
        if not self.config:
            return
        
        from telegram import Bot
        from core.security import decrypt_key
        
        token = decrypt_key(self.config.telegram.bot_token)
        bot = Bot(token=token)
        
        for user_id in self.config.telegram.allowed_user_ids:
            try:
                # Use a new event loop or the current one
                await bot.send_message(chat_id=user_id, text=f"⚠️ [SIMMI SUPERVISOR]\n{message}")
            except Exception as e:
                logger.error("notify_failed", error=str(e))

    def is_running(self):
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text())
            try:
                # Check if process exists (OS dependent)
                if os.name == 'nt':
                    # Windows
                    output = subprocess.check_output(f'tasklist /fi "PID eq {pid}"', shell=True).decode()
                    return str(pid) in output
                else:
                    # Linux/Unix
                    os.kill(pid, 0)
                    return True
            except (ProcessLookupError, subprocess.CalledProcessError):
                return False
        return False

    def start_background(self):
        """Spawn the supervisor as a background process."""
        if self.is_running():
            print("🚀 Simmi is already running.")
            return

        cmd = [sys.executable, "-m", "core.supervisor", "run-forever"]
        
        # On Windows, we use CREATE_NO_WINDOW or just start it
        if os.name == 'nt':
            # Create a detached process
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS, 
                             stdout=open("logs/supervisor_stdout.log", "a"), 
                             stderr=open("logs/supervisor_stderr.log", "a"),
                             stdin=subprocess.PIPE,
                             cwd=os.getcwd())
        else:
            # Linux daemonizing would go here
            subprocess.Popen(cmd, stdout=open("logs/supervisor_stdout.log", "a"), 
                             stderr=open("logs/supervisor_stderr.log", "a"),
                             preexec_fn=os.setpgrp,
                             cwd=os.getcwd())
        
        print("✅ Simmi started in background (Supervisor Mode)")

    def stop(self):
        if not self.is_running():
            print("🛑 Simmi is not running.")
            return

        pid = int(PID_FILE.read_text())
        print(f"Stopping Simmi (PID: {pid})...")
        try:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=True)
            else:
                os.kill(pid, signal.SIGTERM)
            PID_FILE.unlink()
            print("✅ Simmi stopped.")
        except Exception as e:
            print(f"❌ Failed to stop Simmi: {str(e)}")

    async def run_forever(self):
        """The main loop that keeps the agent alive."""
        # Write PID
        PID_FILE.parent.mkdir(exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
        
        await self._init_notify_channel()
        await self.notify_owner("🚀 Simmi Supervisor started. Monitoring agent...")

        while True:
            logger.info("supervisor_starting_agent")
            
            # Start main.py
            self.process = subprocess.Popen([sys.executable, "main.py"], cwd=os.getcwd())
            
            # Wait for it to exit
            retcode = self.process.wait()
            
            if retcode != 0:
                logger.error("agent_crashed", exit_code=retcode)
                await self.notify_owner(f"❌ Simmi Agent crashed with exit code {retcode}. Restarting in 5 seconds...")
            else:
                logger.info("agent_stopped_cleanly")
                await self.notify_owner("ℹ️ Simmi Agent stopped cleanly. Restarting...")

            time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run-forever":
        supervisor = SimmiSupervisor()
        asyncio.run(supervisor.run_forever())
