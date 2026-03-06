import typer
import asyncio
import questionary
import yaml
import os
import sys
import time
import subprocess
from pathlib import Path
from halo import Halo
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich import box
from typing import Optional

from cli.utils import print_banner, print_step, print_error, print_success, create_status_table
from core.schemas import SimmiConfig, LLMConfig, TelegramConfig, DatabaseConfig, PersonalityConfig, WhatsAppConfig
from core.security import encrypt_key
from core.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("cli")
app = typer.Typer(
    help="🤖 Simmi Agent - Premium Autonomous AI Control (mimicking OpenClaw logic)",
    add_completion=False,
    no_args_is_help=True
)
console = Console()

def get_config():
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        return None
    with open(config_path, "r") as f:
        return SimmiConfig(**yaml.safe_load(f))

@app.command()
def init():
    """🚀 Launch the interactive production setup wizard."""
    print_banner()
    console.print(Panel("[bold white]Welcome to the Simmi Agent Setup Wizard[/bold white]\n[dim]This will securely configure your AI agent for production use.[/dim]", border_style="cyan"))
    
    # Check if config exists
    if Path("config/config.yaml").exists():
        if not questionary.confirm("⚠️ Config file already exists. Overwrite?").ask():
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
        print_success("Simmi Agent is ready. Configuration is encrypted and stored locally.")
        console.print("\n💡 [dim]Run 'simmi doctor' to verify connections or 'simmi start' to boot.[/dim]")
        
    except Exception as e:
        spinner.fail(f"Initialization failed: {str(e)}")
        logger.error("init_failed", error=str(e))

@app.command()
def config():
    """⚙️ View the current (non-sensitive) configuration."""
    print_banner()
    c = get_config()
    if not c:
        print_error("No config found. Run 'simmi init' first.")
        return
        
    table = Table(title="⚙️ Simmi Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Agent Name", c.personality.name)
    table.add_row("Owner", c.personality.owner)
    table.add_row("Tone", c.personality.tone)
    table.add_row("Role", c.personality.role)
    table.add_row("LLM Provider", c.llm.provider)
    table.add_row("Voice Interface", "ENABLED" if c.voice.enabled else "DISABLED")
    table.add_row("WhatsApp Enabled", "YES" if c.whatsapp.enabled else "NO")
    
    console.print(table)
    console.print("\n[dim]Sensitive keys are encrypted and hidden for your security.[/dim]")

@app.command()
def chat():
    """💬 Start an interactive high-speed chat with Simmi directly in CLI."""
    print_banner()
    config = get_config()
    if not config:
        print_error("Configuration not found. Please run 'simmi init' first.")
        return

    from core.agent import SimmiAgent
    agent = SimmiAgent(config)
    
    console.print(Panel(f"Chatting with [bold cyan]{agent.personality_name}[/bold cyan] (Owner: {agent.personality_owner})\n[dim]Type 'exit' to quit.[/dim]", border_style="green"))

    while True:
        try:
            user_input = Prompt.ask("\n[bold white]You[/bold white]")
            if user_input.lower() in ["exit", "quit", "/exit"]:
                break
            
            with console.status(f"[bold dim]{agent.personality_name} is thinking...[/bold dim]"):
                # Use a dummy system user ID for CLI chat
                response = asyncio.run(agent.handle_message("cli_user", user_input))
            
            console.print(f"\n[bold cyan]{agent.personality_name}:[/bold cyan]")
            console.print(Markdown(response))
        except KeyboardInterrupt:
            break
        except Exception as e:
            print_error(f"Chat error: {str(e)}")

@app.command()
def doctor():
    """🏥 Run real system diagnostics and health checks."""
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
    """📡 Show the real-time production health of Simmi."""
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

    results = asyncio.run(run_diagnostics())
    
    comp_map = {
        "Database": "Database",
        "Redis": "Redis",
        "Telegram": "Telegram Bot",
        "WhatsApp": "WhatsApp",
        "Voice": "Voice System"
    }

    for name, data in results.items():
        comp_name = comp_map.get(name, name)
        status_fmt = f"[green]CONNECTED[/green]" if data["status"] == "ok" else f"[red]ERROR[/red]"
        table.add_row(comp_name, status_fmt, data["message"])
    
    table.add_row("Scheduler", "[green]ACTIVE[/green]" if is_up else "[dim]INACTIVE[/dim]", "Job queue running")
    
    console.print(table)
    if not is_up:
        console.print("\n💡 [yellow]Tip:[/yellow] Run 'simmi start' to boot the agent service.\n")

@app.command()
def start(background: bool = typer.Option(True, "--no-background", flag_value=False, help="Run in foreground mode")):
    """🚀 Start the Simmi Agent services."""
    print_banner()
    from core.supervisor import SimmiSupervisor
    supervisor = SimmiSupervisor()
    
    if background:
        print_step("Initializing Simmi Lifecycle Manager (Background)...")
        supervisor.start_background()
    else:
        print_step("Starting services in foreground (Production Mode)...")
        asyncio.run(supervisor.run_forever())

@app.command()
def stop():
    """🛑 Stop the running Simmi Agent service."""
    from core.supervisor import SimmiSupervisor
    SimmiSupervisor().stop()

@app.command()
def tools():
    """🛠️ List all registered tools and their capabilities."""
    print_banner()
    config = get_config()
    if not config:
        print_error("Configuration not found.")
        return

    from core.agent import SimmiAgent
    agent = SimmiAgent(config)
    
    table = Table(title="Available Tools", box=box.ROUNDED)
    table.add_column("Tool Name", style="cyan")
    table.add_column("Description", style="dim")
    
    for tool in agent.registry.list_tools():
        table.add_row(tool["name"], tool["description"])
    
    console.print(table)

@app.command(name="whatsapp")
def whatsapp_cmd(action: str = typer.Argument("status", help="Action: link, status")):
    """📱 WhatsApp integration management."""
    print_banner()
    if action == "link":
        print_step("Initializing WhatsApp Link Session...")
        print_step("Scan the QR Code below with your WhatsApp app.")
        
        if os.name == 'nt':
            try:
                out = subprocess.check_output('netstat -ano | findstr :3000', shell=True).decode()
                for line in out.splitlines():
                    if "LISTENING" in line:
                        pid = line.strip().split()[-1]
                        subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True)
            except Exception: pass
        else:
            os.system("fuser -k 3000/tcp > /dev/null 2>&1")

        bridge_path = Path("whatsapp_bridge")
        try:
            subprocess.run(["node", "index.js"], cwd=bridge_path)
        except KeyboardInterrupt:
            print_success("Link ended.")
        except Exception as e:
            print_error(f"Failed: {str(e)}")

    elif action == "status":
        import httpx
        try:
            resp = httpx.get("http://localhost:3000/status", timeout=5)
            data = resp.json()
            table = Table(title="📱 WhatsApp Status", box=box.ROUNDED)
            table.add_column("Property", style="cyan")
            table.add_row("Connection", "[bold green]CONNECTED[/bold green]" if data.get("connected") else "[yellow]UNLINKED[/yellow]")
            table.add_row("Number", data.get("number", "N/A"))
            table.add_row("Uptime", str(data.get("uptime", "N/A")))
            console.print(table)
        except Exception:
            print_error("WhatsApp bridge is not running.")

@app.command()
def logs(follow: bool = typer.Option(False, "--follow", "-f", help="Stream logs"), 
         n: int = typer.Option(20, "--n", "-n", help="Number of lines")):
    """📜 Stream or view the system logs."""
    log_file = Path("logs/simmi.log")
    if not log_file.exists():
        print_error("No logs found.")
        return
        
    if follow:
        try:
            with open(log_file, "r") as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    console.print(line.strip())
        except KeyboardInterrupt:
            pass
    else:
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-n:]:
                console.print(line.strip())

if __name__ == "__main__":
    app()
