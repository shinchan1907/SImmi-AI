import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

def print_banner():
    banner = pyfiglet.figlet_format("SIMMI AGENT", font="slant")
    console.print(Panel(Text(banner, style="cyan bold"), border_style="blue", box=box.DOUBLE))
    console.print("[bold blue]Production-Grade Autonomous AI Framework[/bold blue]", justify="center")
    console.print("---" * 20, justify="center")

def print_step(message: str):
    console.print(f"[bold green]➜[/bold green] {message}")

def print_error(message: str):
    console.print(f"[bold red]✘ Error:[/bold red] {message}")

def print_success(message: str):
    console.print(f"[bold green]✔ Success:[/bold green] {message}")

def create_status_table():
    table = Table(title="System Status", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    return table
