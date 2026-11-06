"""
Media Studio Automater - Background Automation Daemon
Runs continuously and triggers scheduled posts at specific times.
Works like X automater - keeps running even if you close the terminal.
"""
import sys
import os
import time
import json
import schedule
import subprocess
from pathlib import Path
from datetime import datetime
from rich.console import Console

console = Console()

BASE_DIR = Path(__file__).resolve().parent.parent

REELS_SHORT_TIMES = ["17:15", "19:15"]  # 5:15 PM and 7:15 PM daily
EXPLAINER_TIME = "21:15"  # 9:15 PM on alternate days

class AutomationDaemon:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.reels_times_run_today = set()
        self.last_explainer_run = None
        self.history_file = BASE_DIR / "studio_history.json"
        self._setup_schedule()

    def _setup_schedule(self):
        for t in REELS_SHORT_TIMES:
            schedule.every().day.at(t).do(self._run_reels_shorts)
            console.print(f"[green]✅ Scheduled Reels/Shorts at {t}[/green]")
        schedule.every().day.at(EXPLAINER_TIME).do(self._run_explainer)
        console.print(f"[green]✅ Scheduled Explainer at {EXPLAINER_TIME} (alternate days)[/green]")

    def _is_alternate_day(self) -> bool:
        try:
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                events = data.get("events", [])
                last_explainer = None
                for event in reversed(events):
                    if event.get("type") == "explainer_video":
                        last_explainer = event.get("time", "")
                        break
                if last_explainer:
                    last_dt = datetime.strptime(last_explainer, "%Y-%m-%d %I:%M %p")
                    today = datetime.now()
                    days_diff = (today.date() - last_dt.date()).days
                    return days_diff >= 2
                return True
        except Exception:
            return True
        return True

    def _run_reels_shorts(self):
        now_str = datetime.now().strftime("%H:%M")
        today = datetime.now().strftime("%Y-%m-%d")
        if now_str in self.reels_times_run_today:
            return
        # Reset set if new day
        if hasattr(self, '_reels_day') and self._reels_day != today:
            self.reels_times_run_today.clear()
        self._reels_day = today
        self.reels_times_run_today.add(now_str)
        now = datetime.now().strftime("%I:%M %p")
        console.print(f"\n[bold cyan]⏰ [{now}] Running scheduled Reels/Shorts pipeline...[/bold cyan]")
        cmd = [sys.executable, str(BASE_DIR / "main.py"), "schedule-reels-shorts"]
        if self.dry_run:
            cmd.append("--dry-run")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=600)
            console.print(f"[bold green]✅ Reels/Shorts completed at {now}[/bold green]")
            if result.stdout:
                console.print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Reels/Shorts timed out[/red]")
        except Exception as e:
            console.print(f"[red]❌ Reels/Shorts error: {e}[/red]")

    def _run_explainer(self):
        now = datetime.now().strftime("%I:%M %p")
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_explainer_run == today:
            return
        if not self._is_alternate_day():
            console.print(f"[yellow]⚠️ [{now}] Not an alternate day - skipping explainer[/yellow]")
            return
        console.print(f"\n[bold magenta]⏰ [{now}] Running scheduled Explainer pipeline...[/bold magenta]")
        cmd = [sys.executable, str(BASE_DIR / "main.py"), "schedule-explainer"]
        if self.dry_run:
            cmd.append("--dry-run")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=900)
            console.print(f"[bold green]✅ Explainer completed at {now}[/bold green]")
            if result.stdout:
                console.print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Explainer timed out[/red]")
        except Exception as e:
            console.print(f"[red]❌ Explainer error: {e}[/red]")
        self.last_explainer_run = today

    def run(self):
        console.print("\n" + "="*60, style="bold cyan")
        console.print("🤖 MEDIA STUDIO AUTOMATION DAEMON", style="bold magenta")
        console.print("="*60, style="bold cyan")
        console.print(f"\n[bold]Scheduled Tasks:[/bold]")
        console.print(f"  📺 Reels/Shorts: Daily at {REELS_SHORT_TIMES[0]} & {REELS_SHORT_TIMES[1]}")
        console.print(f"  🎬 Explainer: Daily at {EXPLAINER_TIME} (alternate days)")
        console.print(f"\n[bold yellow]Press Ctrl+C to stop[/bold yellow]\n")
        schedule.run_pending()
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]🛑 Automation daemon stopped[/bold yellow]")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Media Studio Automation Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Run in simulation mode")
    args = parser.parse_args()
    daemon = AutomationDaemon(dry_run=args.dry_run)
    daemon.run()

if __name__ == "__main__":
    main()
