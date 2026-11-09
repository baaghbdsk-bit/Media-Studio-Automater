"""
Media Studio Automater - Background Automation Daemon
Runs continuously and triggers scheduled posts at specific times.
Works like X automater - keeps running even if you close the terminal.
"""
import sys
import time
import schedule
import subprocess
from pathlib import Path
from datetime import datetime
from rich.console import Console

console = Console()

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "output" / "automation.log"

REELS_SHORT_TIMES = ["17:15", "19:15"]  # 5:15 PM and 7:15 PM daily
EXPLAINER_TIME = "21:15"  # 9:15 PM on alternate days

class AutomationDaemon:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.reels_times_run_today = set()
        self.last_explainer_run = None
        self._setup_schedule()

    def _setup_schedule(self):
        for t in REELS_SHORT_TIMES:
            schedule.every().day.at(t).do(self._run_reels_shorts)
            console.print(f"[green]✅ Scheduled Reels/Shorts at {t}[/green]")
        schedule.every().day.at(EXPLAINER_TIME).do(self._run_explainer)
        console.print(f"[green]✅ Scheduled Explainer at {EXPLAINER_TIME} (alternate days)[/green]")

    def _run_pipeline(self, action: str, timeout: int) -> bool:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %I:%M:%S %p")
        label = "Explainer" if action == "schedule-explainer" else "Reels/Shorts"
        console.print(f"\n[bold cyan]⏰ [{now.strftime('%I:%M %p')}] Running scheduled {label} pipeline...[/bold cyan]")
        cmd = [sys.executable, str(BASE_DIR / "main.py"), action]
        if self.dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            errors = exc.stderr or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            if isinstance(errors, bytes):
                errors = errors.decode("utf-8", errors="replace")
            self._write_run_log(timestamp, action, output, errors, "Timed out")
            console.print(f"[red]❌ {label} timed out after {timeout} seconds. See {LOG_FILE}[/red]")
            return False
        except OSError as exc:
            self._write_run_log(timestamp, action, "", str(exc), "Could not start")
            console.print(f"[red]❌ Could not start {label}: {exc}. See {LOG_FILE}[/red]")
            return False

        status = "Succeeded" if result.returncode == 0 else f"Failed (exit code {result.returncode})"
        self._write_run_log(timestamp, action, result.stdout, result.stderr, status)
        if result.returncode == 0:
            console.print(f"[bold green]✅ {label} completed at {now.strftime('%I:%M %p')}[/bold green]")
        else:
            console.print(f"[red]❌ {label} failed with exit code {result.returncode}. See {LOG_FILE}[/red]")
        if result.stdout:
            console.print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr[-500:]}[/red]")
        return result.returncode == 0

    @staticmethod
    def _write_run_log(timestamp: str, action: str, stdout: str, stderr: str, status: str):
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as log:
                log.write(f"\n[{timestamp}] {action}: {status}\n")
                if stdout:
                    log.write(stdout)
                    if not stdout.endswith("\n"):
                        log.write("\n")
                if stderr:
                    log.write("[stderr]\n")
                    log.write(stderr)
                    if not stderr.endswith("\n"):
                        log.write("\n")
        except OSError as exc:
            console.print(f"[red]❌ Could not write automation log {LOG_FILE}: {exc}[/red]")

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
        self._run_pipeline("schedule-reels-shorts", 600)

    def _run_explainer(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_explainer_run == today:
            return
        self._run_pipeline("schedule-explainer", 900)
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
    parser.add_argument(
        "action",
        nargs="?",
        choices=("schedule-reels-shorts", "schedule-explainer"),
        help="Run one scheduled pipeline and exit instead of starting the daemon",
    )
    args = parser.parse_args()
    daemon = AutomationDaemon(dry_run=args.dry_run)
    if args.action == "schedule-reels-shorts":
        sys.exit(0 if daemon._run_pipeline(args.action, 600) else 1)
    if args.action == "schedule-explainer":
        sys.exit(0 if daemon._run_pipeline(args.action, 900) else 1)
    daemon.run()

if __name__ == "__main__":
    main()
