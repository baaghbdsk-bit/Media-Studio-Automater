"""Media Studio Automater CLI.
Autonomous Production Studio for YouTube Shorts, Instagram Reels, and Pinterest.
"""
import sys
import subprocess
import time
from pathlib import Path

# Auto-detect and use virtualenv python (check local or sibling X-Post-Automater venv)
_BASE_DIR = Path(__file__).resolve().parent
_LOCAL_VENV_PY = _BASE_DIR / "venv" / "Scripts" / "python.exe"
_SIBLING_VENV_PY = Path("E:/X-Post-Automater/venv/Scripts/python.exe")
_TARGET_PY = _LOCAL_VENV_PY if _LOCAL_VENV_PY.exists() else (_SIBLING_VENV_PY if _SIBLING_VENV_PY.exists() else None)

if _TARGET_PY and Path(sys.executable).resolve() != _TARGET_PY.resolve():
    try:
        sys.exit(subprocess.call([str(_TARGET_PY)] + sys.argv))
    except Exception:
        pass

import argparse
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def display_metrics():
    history_file = _BASE_DIR / "studio_history.json"
    if not history_file.exists():
        console.print("[yellow]No studio_history.json found yet.[/yellow]")
        return
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        topics = data.get("posted_topics", [])
        events = data.get("events", [])
        
        console.print("\n" + "="*60, style="bold cyan")
        console.print("🎬 MEDIA STUDIO AUTOMATER METRICS", style="bold magenta")
        console.print(f"Total Published Topics: {len(topics)} | Events Recorded: {len(events)}")
        console.print("="*60, style="bold cyan")
        
        if topics:
            table = Table(title="Recent Published Topics")
            table.add_column("#", style="dim", width=4)
            table.add_column("Topic Title", style="bold green")
            for idx, top in enumerate(topics[-10:], 1):
                table.add_row(str(idx), str(top))
            console.print(table)
    except Exception as e:
        console.print(f"[red]Error reading metrics: {e}[/red]")

def run_doctor():
    console.print("\n" + "="*60, style="bold cyan")
    console.print("🩺 MEDIA STUDIO HEALTH & AUTH DOCTOR", style="bold white on cyan")
    console.print("="*60, style="bold cyan")

    table = Table(title="Channel Authentication & Pipeline Health")
    table.add_column("Channel / Component", style="bold cyan", width=22)
    table.add_column("Status", width=16)
    table.add_column("Diagnostic Details", style="dim")

    # 1. Gemini AI API
    try:
        import config
        from google import genai
        if getattr(config, "GEMINI_API_KEY", ""):
            table.add_row("Gemini AI API", "[green]ONLINE[/green]", "API key configured & ready")
        else:
            table.add_row("Gemini AI API", "[red]MISSING[/red]", "GEMINI_API_KEY not set")
    except Exception as e:
        table.add_row("Gemini AI API", "[yellow]WARNING[/yellow]", str(e)[:60])

    # 2. YouTube Data API v3
    try:
        from src.youtube_automater import YouTubeAutomater
        yt = YouTubeAutomater()
        if yt.is_authenticated:
            table.add_row("YouTube Data API", "[green]AUTHENTICATED[/green]", "Permanent OAuth refresh token active & verified")
        else:
            table.add_row("YouTube Data API", "[red]DISCONNECTED[/red]", "Token expired or missing. Run 'python scripts/login_youtube.py'")
    except Exception as e:
        table.add_row("YouTube Data API", "[red]ERROR[/red]", str(e)[:60])

    # 3. Instagram Reels
    try:
        from src.instagram_automater import InstagramAutomater
        ig = InstagramAutomater(headless=True)
        if ig.is_session_available():
            table.add_row("Instagram (@neubench)", "[green]AUTHENTICATED[/green]", "Valid session cookies loaded")
        else:
            table.add_row("Instagram (@neubench)", "[red]DISCONNECTED[/red]", "Session missing. Set INSTAGRAM_COOKIES_BASE64")
    except Exception as e:
        table.add_row("Instagram (@neubench)", "[red]ERROR[/red]", str(e)[:60])

    # 4. Pinterest Video Pins
    try:
        from src.pinterest_automater import PinterestAutomater
        pin = PinterestAutomater(headless=True)
        if pin.is_session_available():
            table.add_row("Pinterest (@neubench)", "[green]AUTHENTICATED[/green]", "Session cookies loaded & video upload enabled")
        else:
            table.add_row("Pinterest (@neubench)", "[red]DISCONNECTED[/red]", "Session missing. Run 'python scripts/login_pinterest.py'")
    except Exception as e:
        table.add_row("Pinterest (@neubench)", "[red]ERROR[/red]", str(e)[:60])

    # 5. Threads
    try:
        from src.threads_automater import ThreadsAutomater
        th = ThreadsAutomater(headless=True)
        if th.is_session_available():
            table.add_row("Threads", "[green]AUTHENTICATED[/green]", "Dedicated threads.net session active")
        else:
            table.add_row("Threads", "[yellow]CROSSPOST[/yellow]", "Using Instagram 'Share to Threads' integration")
    except Exception as e:
        table.add_row("Threads", "[dim]ERROR[/dim]", str(e)[:60])

    console.print(table)

def main():
    parser = argparse.ArgumentParser(
        description="Media Studio Automater: High-Impact Video & Visual Publishing Suite for YouTube Shorts, Instagram Reels, and Pinterest"
    )
    parser.add_argument(
        "action",
        choices=[
            "studio-all",
            "post-all",
            "youtube",
            "instagram-reel",
            "pinterest",
            "threads",
            "youtube-explainer",
            "long-explainer",
            "generate-video",
            "ig-diagnose",
            "metrics",
            "doctor",
            "schedule-autopilot",
            "schedule-reels-shorts",
            "schedule-explainer",
            "schedule-today"
        ],
        help="Action to perform"
    )
    parser.add_argument("--dry-run", action="store_true", help="Run in simulation mode without publishing live")
    parser.add_argument("--topic", type=str, default="", help="Custom topic to generate content for")

    args = parser.parse_args()

    if args.action == "metrics":
        display_metrics()
        return

    if args.action == "doctor":
        run_doctor()
        return

    from src.studio_engine import StudioEngine

    engine = StudioEngine(dry_run=args.dry_run)

    if args.action in ("studio-all", "post-all"):
        console.print(f"[bold cyan]🚀 Triggering Studio Broadcast Cycle (Dry-run: {args.dry_run})...[/bold cyan]")
        engine.run_studio_all()

    elif args.action == "youtube":
        console.print(f"[bold cyan]🎬 Publishing YouTube Short (Dry-run: {args.dry_run})...[/bold cyan]")
        engine.publish_youtube()

    elif args.action == "instagram-reel":
        console.print(f"[bold magenta]🎥 Publishing Instagram Reel (Dry-run: {args.dry_run})...[/bold magenta]")
        engine.publish_instagram_reel()

    elif args.action == "pinterest":
        console.print(f"[bold red]📌 Publishing Pinterest Pin (Dry-run: {args.dry_run})...[/bold red]")
        engine.publish_pinterest()

    elif args.action == "generate-video":
        console.print(f"[bold cyan]⏳ Synthesizing Video only...[/bold cyan]")
        from src.video_generator import VideoGenerator
        topic = {"title": args.topic} if args.topic else engine.get_fresh_topic()
        res = VideoGenerator().generate_dynamic_short(topic, dry_run=args.dry_run)
        console.print(f"[bold green]Video generated: {res}[/bold green]")

    elif args.action == "ig-diagnose":
        from scripts import ig_diagnose
        exit_code = ig_diagnose.main()
        console.print(f"[bold green]IG Diagnostic completed (exit code {exit_code})[/bold green]")

    elif args.action == "youtube-explainer":
        console.print(f"[bold magenta]🎬 Publishing 16:9 YouTube Long Explainer (Dry-run: {args.dry_run})...[/bold magenta]")
        engine.publish_youtube_explainer()

    elif args.action == "long-explainer":
        console.print(f"[bold magenta]🎬 Running scheduled Long Explainer slot (Dry-run: {args.dry_run})...[/bold magenta]")
        engine.run_long_explainer_slot()

    elif args.action == "threads":
        console.print(f"[bold magenta]🧵 Publishing to Threads (Dry-run: {args.dry_run})...[/bold magenta]")
        engine.publish_threads()

    elif args.action == "schedule-autopilot":
        console.print(f"[bold cyan]⏰ Running 4-Hour Autopilot Cycle (Dry-run: {args.dry_run})...[/bold cyan]")
        engine.schedule_autopilot()

    elif args.action == "schedule-reels-shorts":
        console.print(f"[bold cyan]⏰ Running scheduled Reels/Shorts...[/bold cyan]")
        engine.run_studio_all()

    elif args.action == "schedule-explainer":
        console.print(f"[bold magenta]⏰ Running scheduled Explainer...[/bold magenta]")
        engine.run_long_explainer_slot()

    elif args.action == "schedule-today":
        from datetime import datetime
        current_time = datetime.now().strftime("%I:%M %p")
        console.print(f"[bold cyan]Current time: {current_time}[/bold cyan]")
        if current_time in ["05:15 PM", "07:15 PM"]:
            console.print(f"[bold green]Running scheduled Reels/Shorts publish...[/bold green]")
            engine.run_studio_all()
        elif current_time == "09:15 PM":
            console.print(f"[bold magenta]Running scheduled Explainer video publish...[/bold magenta]")
            import json
            history_file = _BASE_DIR / "studio_history.json"
            should_run = True
            if history_file.exists():
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                events = data.get("events", [])
                last_explainer = None
                for event in reversed(events):
                    if event.get("type") == "explainer_video":
                        last_explainer = event.get("time", "")
                        break
                if last_explainer:
                    from datetime import datetime
                    last_dt = datetime.strptime(last_explainer, "%Y-%m-%d %I:%M %p")
                    today = datetime.now()
                    days_diff = (today - last_dt).days
                    if days_diff >= 2:
                        console.print(f"[green]Alternate day confirmed - generating Manim explainer[/green]")
                    else:
                        console.print(f"[yellow]Not an alternate day (last was {days_diff} days ago)[/yellow]")
                        should_run = False
            if should_run:
                engine.run_studio_all()
        else:
            console.print(f"[yellow]Not a scheduled time. Current time: {current_time}[/yellow]")
            console.print(f"Scheduled times: 5:15 PM, 7:15 PM (Reels/Shorts), 9:15 PM (Explainer - alternate days)")

if __name__ == "__main__":
    main()