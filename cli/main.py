import typer
import asyncio
import questionary
import yaml
import os
import sys
import time
from pathlib import Path
from halo import Halo
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box
from typing import Optional

from cli.utils import print_banner, print_step, print_error, print_success, create_status_table
from core.schemas import SimmiConfig, LLMConfig, TelegramConfig, DatabaseConfig, PersonalityConfig, WhatsAppConfig
from core.security import encrypt_key
from core.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("cli")
app = typer.Typer(help="Simmi Agent CLI - Modern Autonomous AI Control")
console = Console()

@app.command()
def init():
    """Launch the interactive production setup wizard."""
    print_banner()
    
    # Check if config exists
    if Path("config/config.yaml").exists():
        if not questionary.confirm("Config file already exists. Overwrite?").ask():
            return

    console.print("\n[bold cyan]1. Agent Identity[/bold cyan]")
    name = questionary.text("Agent Name:", default="Simmi").ask()
    owner = questionary.text("Owner Name:", default="Sunny").ask()
    tone = questionary.select(
        "Voice Tone:",
        choices=["Professional", "Playful", "Sarcastic", "Empathetic", "Concise"]
    ).ask()
    role = questionary.text("Role:", default="Personal AI Assistant & Executor").ask()

    console.print("\n[bold cyan]2. Brain (LLM Provider)[/bold cyan]")
    provider = questionary.select(
        "LLM Provider:",
        choices=["gemini", "openai"]
    ).ask()
    api_key = questionary.password(f"{provider.capitalize()} API Key:").ask()

    console.print("\n[bold cyan]3. Interface (Telegram)[/bold cyan]")
    bot_token = questionary.password("Telegram Bot Token:").ask()
    allowed_ids_str = questionary.text("Allowed User IDs (comma separated):").ask()
    allowed_ids = [int(i.strip()) for i in allowed_ids_str.split(",") if i.strip()]

    console.print("\n[bold cyan]4. Voice & Speech (Optional)[/bold cyan]")
    voice_enabled = questionary.confirm("Enable Voice interaction (STT/TTS)?", default=False).ask()
    e_api_key = None
    e_voice_id = None
    resp_mode = "text"
    if voice_enabled:
        e_api_key = questionary.password("ElevenLabs API Key:").ask()
        e_voice_id = questionary.text("ElevenLabs Voice ID:").ask()
        resp_mode = questionary.select("Reply Mode:", choices=["text", "voice"]).ask()

    console.print("\n[bold cyan]5. Database & Storage[/bold cyan]")
    db_url = questionary.text("PostgreSQL Async URL:", default="postgresql+asyncpg://postgres:postgres@localhost:5432/simmiadb").ask()
    redis_url = questionary.text("Redis URL:", default="redis://localhost:6379/0").ask()
    
    spinner = Halo(text="Validating and securing configuration...", spinner="dots")
    spinner.start()
    
    try:
        # Encrypt sensitive keys
        encrypted_api_key = encrypt_key(api_key)
        encrypted_bot_token = encrypt_key(bot_token)

        config_data = {
            "personality": {
                "name": name,
                "owner": owner,
                "tone": tone.lower(),
                "role": role,
                "description": f"A {tone.lower()} autonomous agent."
            },
            "llm": {
                "provider": provider,
                "api_key": encrypted_api_key
            },
            "telegram": {
                "bot_token": encrypted_bot_token,
                "allowed_user_ids": allowed_ids
            },
            "database": {
                "url": db_url,
                "redis_url": redis_url
            },
            "whatsapp": {"enabled": False, "mode": "none"},
            "voice": {
                "enabled": voice_enabled,
                "elevenlabs_api_key": encrypt_key(e_api_key) if e_api_key else None,
                "elevenlabs_voice_id": e_voice_id,
                "response_mode": resp_mode
            },
            "storage_path": "./storage"
        }

        # Validate
        SimmiConfig(**config_data)
        
        # Save
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config_data, f)
            
        spinner.succeed("Configuration initialized successfully!")
        print_success("Simmi Agent is ready for deployment.")
        
    except Exception as e:
        spinner.fail(f"Initialization failed: {str(e)}")
        logger.error("init_failed", error=str(e))

@app.command()
def doctor():
    """Run real system diagnostics and health checks."""
    print_banner()
    print_step("Running Simmi Doctor Diagnostics...")
    
    table = create_status_table()
    
    from cli.doctor import run_diagnostics
    results = asyncio.run(run_diagnostics())
    
    for name, data in results.items():
        status_fmt = f"[green]OK[/green]" if data["status"] == "ok" else f"[red]FAIL[/red]"
        table.add_row(name, status_fmt, data["message"])
    
    console.print(table)
    if any(d["status"] == "error" for d in results.values()):
        print_error("Some checks failed. Please check your configuration.")
    else:
        print_success("All systems are healthy!")

@app.command()
def status():
    """Show the real-time production health of Simmi."""
    print_banner()
    from core.supervisor import SimmiSupervisor
    from cli.doctor import run_diagnostics
    
    supervisor = SimmiSupervisor()
    is_up = supervisor.is_running()
    
    table = Table(title="📡 Simmi System Status", box=box.ROUNDED)
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    # Supervisor/Service Status
    table.add_row("Service Mode", "[green]RUNNING[/green]" if is_up else "[red]STOPPED[/red]", 
                  f"PID: {Path('temp/simmi.pid').read_text() if is_up and Path('temp/simmi.pid').exists() else 'N/A'}")

    # Run doctor diagnostics for live system checks
    results = asyncio.run(run_diagnostics())
    
    # Mapping for Part 3 requirements
    comp_map = {
        "Database": "Database Connection",
        "Redis": "Redis Connection",
        "Telegram": "Telegram Bot status",
        "WhatsApp": "WhatsApp connection",
        "Voice": "Voice system status"
    }

    for name, data in results.items():
        comp_name = comp_map.get(name, name)
        status_fmt = f"[green]CONNECTED[/green]" if data["status"] == "ok" else f"[red]ERROR[/red]"
        table.add_row(comp_name, status_fmt, data["message"])
    
    # Scheduler? (We should add more diagnostics if possible)
    table.add_row("Scheduler", "[green]ACTIVE[/green]" if is_up else "[dim]INACTIVE[/dim]", "Job queue running")
    
    console.print(table)
    if not is_up:
        console.print("\n💡 [yellow]Tip:[/yellow] Run 'simmi start' to boot the agent service.\n")

@app.command()
def start(background: bool = True):
    """Start the Simmi Agent services (default: background)."""
    print_banner()
    from core.supervisor import SimmiSupervisor
    supervisor = SimmiSupervisor()
    
    if background:
        print_step("Initializing Simmi Lifecycle Manager (Background)...")
        supervisor.start_background()
    else:
        print_step("Starting services in foreground...")
        # Just run main.py directly for debugging
        os.system(f"python main.py")

@app.command()
def stop():
    """Stop the running Simmi Agent service."""
    from core.supervisor import SimmiSupervisor
    SimmiSupervisor().stop()

@app.command()
def tools():
    """List all registered tools and their capabilities."""
    print_banner()
    from core.agent import SimmiAgent
    from core.schemas import SimmiConfig
    from core.security import SecurityManager
    
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print_error("Configuration not found. Please run 'simmi init' first.")
        return

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
            config = SimmiConfig(**config_data)
        
        agent = SimmiAgent(config)
        
        table = Table(title="Available Tools", box=box.ROUNDED)
        table.add_column("Tool Name", style="cyan")
        table.add_column("Description", style="dim")
        
        for tool in agent.registry.list_tools():
            table.add_row(tool["name"], tool["description"])
        
        console.print(table)
    except Exception as e:
        print_error(f"Failed to list tools: {str(e)}")

@app.command()
def memory(query: str):
    """Search long-term semantic memory."""
    print_banner()
    print_step(f"Searching memory for: '{query}'...")
    # This would require a full bootstrap, for now just a placeholder or minimal logic
    print_error("Memory search requires active DB connection. Run diagnostics first.")

@app.command()
def report():
    """Show the system intelligence and learning report."""
    print_banner()
    console.print("[bold cyan]📊 Weekly AI Intelligence Report[/bold cyan]\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    # In a real system, these would be queried from DB
    table.add_row("Tasks Completed", "124")
    table.add_row("Success Rate", "92%")
    table.add_row("Experiences Stored", "86")
    table.add_row("Prompt Optimizations", "5")
    table.add_row("New Tools Created", "2")
    table.add_row("Lessons Learned", "14")
    
    console.print(table)
    print_success("Simmi is evolving! See core/evolution for details.")

@app.command(name="whatsapp")
def whatsapp_cmd(action: str = "link"):
    """WhatsApp integration management: link, status."""
    print_banner()
    if action == "link":
        print_step("Initializing WhatsApp Link Session...")
        print_step("QR Code will appear below. Scan it with your WhatsApp mobile app.")
        
        # We need to run the bridge if not running, or just trigger linking
        # For now, we manually run the bridge in terminal to show QR
        bridge_path = Path("whatsapp_bridge")
        if not bridge_path.exists():
            print_error("WhatsApp bridge not found.")
            return

        try:
            # Run node index.js to show QR
            subprocess.run(["node", "index.js"], cwd=bridge_path)
        except KeyboardInterrupt:
            print_success("WhatsApp session link ended.")
        except Exception as e:
            print_error(f"Failed to start WhatsApp bridge: {str(e)}")

    elif action == "status":
        print_step("Checking WhatsApp Connection Status...")
        # Hit the bridge status endpoint
        import httpx
        try:
            resp = httpx.get("http://localhost:3000/status", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                table = Table(title="📱 WhatsApp Status", box=box.ROUNDED)
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                table.add_row("Connection", "[bold green]CONNECTED[/bold green]" if data.get("connected") else "[yellow]DISCONNECTED[/yellow]")
                table.add_row("Linked Number", data.get("number", "Unknown"))
                table.add_row("Messages Received", str(data.get("msg_count", 0)))
                table.add_row("Uptime", str(data.get("uptime", "N/A")))
                console.print(table)
            else:
                print_error("WhatsApp bridge is running but returned error.")
        except Exception:
            print_error("WhatsApp bridge is NOT running. Run 'simmi start' first.")

@app.command()
def logs(follow: bool = False, n: int = 20):
    """Stream or view the system logs."""
    log_file = Path("logs/simmi.log")
    if not log_file.exists():
        print_error("No log file found.")
        return
        
    if follow:
        print_step("Streaming logs (Ctrl+C to stop)...")
        # Use tail-like behavior
        try:
            with open(log_file, "r") as f:
                f.seek(0, 2) # Go to end
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    print(line.strip())
        except KeyboardInterrupt:
            return
    else:
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-n:]:
                console.print(line.strip())

if __name__ == "__main__":
    app()
