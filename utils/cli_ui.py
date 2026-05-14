"""
CLI UI Module for AI Job Search Agent
Provides a rich, branded terminal experience with animated character and status displays.
"""
import sys
import os
import io
import time
import threading
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich import box

try:
    from rich_pixels import Pixels
    HAS_RICH_PIXELS = True
except ImportError:
    HAS_RICH_PIXELS = False

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Detect CI environment
IS_CI = os.environ.get("CI", "").lower() in ("true", "1", "yes")

console = Console(force_terminal=not IS_CI)

# ── ASCII Art Mascot ──────────────────────────────────────────────
MASCOT_IDLE = r"""
    ╔══════════╗
    ║  ◉    ◉  ║
    ║    ──    ║
    ╚══════════╝
     ┌──┤██├──┐
     │  ╔══╗  │
     │  ║  ║  │
     └──╚══╝──┘
"""

MASCOT_SEARCHING = r"""
    ╔══════════╗
    ║  ◎    ◎  ║
    ║    ▷▷    ║
    ╚══════════╝
     ┌──┤██├──┐  🔍
     │  ╔══╗  │
     │  ║▓▓║  │
     └──╚══╝──┘
"""

MASCOT_MATCHING = r"""
    ╔══════════╗
    ║  ★    ★  ║
    ║    ◡◡    ║
    ╚══════════╝
     ┌──┤██├──┐  📊
     │  ╔══╗  │
     │  ║▒▒║  │
     └──╚══╝──┘
"""

MASCOT_SUCCESS = r"""
    ╔══════════╗
    ║  ✦    ✦  ║
    ║   ╰──╯   ║
    ╚══════════╝
     ┌──┤██├──┐  ✉️
     │  ╔══╗  │
     │  ║██║  │
     └──╚══╝──┘
"""

MASCOT_ERROR = r"""
    ╔══════════╗
    ║  ✕    ✕  ║
    ║    ~~    ║
    ╚══════════╝
     ┌──┤██├──┐  ⚠️
     │  ╔══╗  │
     │  ║░░║  │
     └──╚══╝──┘
"""

BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║             ░█▀█░▀█▀░░░░░█░█░█░█░█▀█░▀█▀░█▀▀░█▀▄               ║
║             ░█▀█░░█░░▄▄▄░█▀█░█░█░█░█░░█░░█▀▀░█▀▄               ║
║             ░▀░▀░▀▀▀░░░░░▀░▀░▀▀▀░▀░▀░░▀░░▀▀▀░▀░▀               ║
║                                                                   ║
║           🤖  AI Job & PhD Search Agent  v2.0  🤖                 ║
║                  by Pallab Mondal                                 ║
╚═══════════════════════════════════════════════════════════════════╝"""


class AgentUI:
    """Rich CLI UI for the Job Search Agent."""

    def __init__(self):
        self.console = console
        self._current_mascot = MASCOT_IDLE
        self._status_text = "Initializing..."
        self._stats = {"scraped": 0, "unique": 0, "matched": 0}
        self._activity_log = []

    def _get_pixel_image(self, path: str, fallback_text: str, color_style: str = "") -> any:
        """Render an image as Pixels, falling back to ASCII text if missing/failed."""
        if IS_CI:
            return Text(fallback_text, style=color_style)
        if HAS_RICH_PIXELS and os.path.exists(path):
            try:
                # Keep terminal width matching size (thumbnail aspect ratio)
                # Max width ~40 chars fits nicely inside a panel of width 50
                from PIL import Image
                from pathlib import Path as _Path
                _Path("data").mkdir(exist_ok=True)
                img = Image.open(path)
                img.thumbnail((36, 36))
                img.save("data/temp_render.png") # temp thumb
                return Pixels.from_image_path("data/temp_render.png")
            except Exception:
                pass
        return Text(fallback_text, style=color_style)

    def show_banner(self):
        """Display the startup banner with mascot."""
        if not IS_CI:
            self.console.clear()
        banner_text = Text(BANNER)
        banner_text.stylize("bold cyan")
        self.console.print(banner_text)
        self.console.print()

        hunter_mascot = self._get_pixel_image("assets/logo_hunter.png", MASCOT_IDLE, "bold green")

        mascot_panel = Panel(
            Align.center(hunter_mascot),
            title="[bold cyan]AI-HUNTER[/bold cyan]",
            subtitle="[dim]Ready to hunt[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(Align.center(mascot_panel, width=50))
        self.console.print()

    def show_config_summary(self, config: dict):
        """Display a summary of the current configuration."""
        table = Table(
            title="⚙️  Agent Configuration",
            box=box.ROUNDED,
            title_style="bold magenta",
            border_style="dim cyan",
            show_lines=True,
        )
        table.add_column("Setting", style="bold white", min_width=20)
        table.add_column("Value", style="green")

        keywords = ", ".join(config.get("search_keywords", []))
        locations = ", ".join(config.get("locations", []))
        sites = ", ".join(config.get("sites_to_scrape", []))

        table.add_row("🔑 Keywords", keywords)
        table.add_row("📍 Locations", locations)
        table.add_row("🌐 Sources", sites)
        table.add_row("📧 Email To", config.get("recipient_email", "N/A"))
        table.add_row("📊 Min Score", str(config.get("min_match_score", 0.5)))
        table.add_row("🔄 Interval", f'{config.get("check_interval_hours", 24)}h')

        self.console.print(table)
        self.console.print()

    def show_phase(self, phase: str, mascot: str = None, style: str = "bold cyan"):
        """Display a phase transition with mascot change."""
        if mascot:
            self._current_mascot = mascot

        phase_panel = Panel(
            Align.center(Text(self._current_mascot, style="bold green")),
            title=f"[{style}]{phase}[/{style}]",
            border_style=style.replace("bold ", ""),
            padding=(0, 2),
        )
        self.console.print()
        self.console.print(Align.center(phase_panel, width=50))
        self.console.print()

    def log_activity(self, message: str, style: str = "white"):
        """Log an activity message."""
        timestamp = time.strftime("%H:%M:%S")
        self.console.print(f"  [dim]{timestamp}[/dim]  [bold cyan]▸[/bold cyan] [{style}]{message}[/{style}]")

    def show_scraping_progress(self, keyword: str, location: str, source: str):
        """Show what's currently being scraped."""
        self.console.print(
            f"  [dim]{time.strftime('%H:%M:%S')}[/dim]  "
            f"[bold yellow]⟳[/bold yellow] "
            f"[white]Scraping[/white] [bold magenta]{source}[/bold magenta] "
            f"for [bold green]\"{keyword}\"[/bold green] "
            f"in [bold blue]{location}[/bold blue]"
        )

    def show_match_table(self, matched_jobs: list):
        """Display matched jobs in a rich table."""
        if not matched_jobs:
            self.console.print(
                Panel(
                    "[yellow]No matches found above the score threshold.[/yellow]",
                    border_style="yellow",
                )
            )
            return

        table = Table(
            title=f"🎯  Matched Positions ({len(matched_jobs)} found)",
            box=box.DOUBLE_EDGE,
            title_style="bold green",
            border_style="green",
            show_lines=True,
            padding=(0, 1),
        )
        table.add_column("#", style="dim", width=3, justify="center")
        table.add_column("Position", style="bold white", max_width=35)
        table.add_column("Company", style="cyan", max_width=20)
        table.add_column("Score", style="bold", justify="center", width=8)
        table.add_column("CV", style="magenta", width=8)
        table.add_column("Link", style="blue", max_width=40)

        for i, (job, score, cv_type) in enumerate(matched_jobs, 1):
            # Color-code score
            if score >= 0.8:
                score_style = "bold green"
            elif score >= 0.6:
                score_style = "bold yellow"
            else:
                score_style = "bold red"

            table.add_row(
                str(i),
                job.get("title", "N/A"),
                job.get("company", "N/A"),
                f"[{score_style}]{score:.0%}[/{score_style}]",
                cv_type,
                job.get("url", "N/A")[:40],
            )

        self.console.print()
        self.console.print(table)
        self.console.print()

    def show_stats_summary(self, scraped: int, unique: int, matched: int):
        """Show final statistics."""
        stats_table = Table(box=box.SIMPLE_HEAVY, border_style="cyan", show_header=False)
        stats_table.add_column("Metric", style="bold white")
        stats_table.add_column("Value", style="bold green", justify="right")

        stats_table.add_row("📦 Total Scraped", str(scraped))
        stats_table.add_row("🔗 Unique (Deduplicated)", str(unique))
        stats_table.add_row("✅ Matched", str(matched))

        panel = Panel(
            stats_table,
            title="[bold cyan]📊 Run Statistics[/bold cyan]",
            border_style="cyan",
        )
        self.console.print(panel)

    def show_completion(self, matched_count: int, dry_run: bool):
        """Show completion screen with happy mascot."""
        if matched_count > 0:
            mascot_fallback = MASCOT_SUCCESS
            msg = f"Found {matched_count} matching positions!"
            color = "green"
            img_path = "assets/logo_hunter.png"
        else:
            mascot_fallback = MASCOT_IDLE
            msg = "No new matches this round. Will try again later."
            color = "yellow"
            img_path = "assets/logo_hunter.png"

        mascot_render = self._get_pixel_image(img_path, mascot_fallback, f"bold {color}")

        completion_panel = Panel(
            Align.center(mascot_render),
            title=f"[bold {color}]✨ Run Complete ✨[/bold {color}]",
            subtitle="[dim]Dry Run[/dim]" if dry_run else f"[dim]Results emailed[/dim]",
            border_style=color,
            padding=(0, 2),
        )
        self.console.print()
        self.console.print(Align.center(completion_panel, width=50))
        self.console.print()

    def show_error(self, message: str):
        """Show an error with the error mascot."""
        error_mascot = self._get_pixel_image("assets/logo_error.png", MASCOT_ERROR, "bold red")
        error_panel = Panel(
            Align.center(error_mascot),
            title="[bold red]⚠️ Error[/bold red]",
            subtitle=f"[red]{message}[/red]",
            border_style="red",
            padding=(0, 2),
        )
        self.console.print(Align.center(error_panel, width=50))

    def show_sleep(self, hours: float):
        """Show the agent going to sleep."""
        self.console.print()
        self.console.print(
            Panel(
                Align.center(
                    Text(MASCOT_IDLE, style="bold dim cyan")
                ),
                title=f"[bold cyan]💤 Sleeping for {hours}h[/bold cyan]",
                subtitle="[dim]Press Ctrl+C to wake up and stop[/dim]",
                border_style="dim cyan",
                padding=(0, 2),
            )
        )


# Singleton instance
ui = AgentUI()
