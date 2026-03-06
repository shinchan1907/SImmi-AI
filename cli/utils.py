import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
import os

console = Console()

def print_banner():
    # Detect window size for better spacing
    try:
        columns = os.get_terminal_size().columns
    except:
        columns = 80
        
    banner_text = pyfiglet.figlet_format("SIMMI", font="slant")
    
    # Create a gradient-like panel (cyan to blue)
    console.print("\n")
    console.print(Panel(
        Text(banner_text, style="bold cyan", justify="center"),
        border_style="bright_blue",
        box=box.ROUNDED,
        title="[bold white]v0.1.0-PRODUCTION[/bold white]",
        title_align="right",
        subtitle="[dim white]The Ultimate Autonomous AI Framework[/dim white]",
        subtitle_align="center"
    ))
    console.print("\n")

def print_step(message: str):
    console.print(f"[bold cyan]➜[/bold cyan] [bold white]{message}[/bold white]")

def print_error(message: str):
    console.print(f"\n[bold red]✘ ERROR[/bold red] [red]{message}[/red]")

def print_success(message: str):
    console.print(f"\n[bold green]✔ SUCCESS[/bold green] [green]{message}[/green]")

def create_status_table():
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold cyan",
        border_style="dim blue",
    )
    table.add_column("Component", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    return table
