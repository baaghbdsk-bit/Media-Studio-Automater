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

    auth_status = {}

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
            auth_status["Gemini AI"] = {"status": "ok"}
        else:
            table.add_row("Gemini AI API", "[red]MISSING[/red]", "GEMINI_API_KEY not set")
            auth_status["Gemini AI"] = {"status": "missing", "detail": "GEMINI_API_KEY not set"}
    except Exception as e:
        table.add_row("Gemini AI API", "[yellow]WARNING[/yellow]", str(e)[:60])

    # 2. YouTube Data API v3
    try:
        from src.youtube_automater import YouTubeAutomater
        yt = YouTubeAutomater()
        if yt.is_authenticated:
            table.add_row("YouTube Data API", "[green]AUTHENTICATED[/green]", "Permanent OAuth refresh token active & verified")
            auth_status["YouTube Data API"] = {"status": "ok"}
        else:
            table.add_row("YouTube Data API", "[red]DISCONNECTED[/red]", "Token expired or missing. Run 'python scripts/login_youtube.py'")
            auth_status["YouTube Data API"] = {
                "status": "disconnected",
                "detail": "Refresh token expired or revoked. Re-run scripts/login_youtube.py and update YOUTUBE_TOKEN_BASE64.",
            }
    except Exception as e:
        table.add_row("YouTube Data API", "[red]ERROR[/red]", str(e)[:60])

    # 3. Instagram Reels
    try:
        from src.instagram_automater import InstagramAutomater
        ig = InstagramAutomater(headless=True)
        if ig.is_session_available():
            table.add_row("Instagram (@neubench)", "[green]AUTHENTICATED[/green]", "Valid session cookies loaded")
            auth_status["Instagram"] = {"status": "ok"}
        else:
            table.add_row("Instagram (@neubench)", "[red]DISCONNECTED[/red]", "Session missing. Set INSTAGRAM_COOKIES_BASE64")
            auth_status["Instagram"] = {"status": "disconnected", "detail": "Set INSTAGRAM_COOKIES_BASE64"}
    except Exception as e:
        table.add_row("Instagram (@neubench)", "[red]ERROR[/red]", str(e)[:60])

    # 4. Pinterest Video Pins
    try:
        from src.pinterest_automater import PinterestAutomater
        pin = PinterestAutomater(headless=True)
        if pin.is_session_available():
            table.add_row("Pinterest (@neubench)", "[green]AUTHENTICATED[/green]", "Session cookies loaded & video upload enabled")
            auth_status["Pinterest"] = {"status": "ok"}
        else:
            table.add_row("Pinterest (@neubench)", "[red]DISCONNECTED[/red]", "Session missing. Run 'python scripts/login_pinterest.py'")
            auth_status["Pinterest"] = {"status": "disconnected", "detail": "Set PINTEREST_COOKIES_BASE64"}
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

    # Machine-readable copy for CI: lets the workflow annotate credential
    # problems without turning the whole (non-fatal) doctor step into a failure.
    try:
        status_path = _BASE_DIR / "output" / "doctor_status.json"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(auth_status, indent=2), encoding="utf-8")
    except Exception:
        pass

def _run_scheduled_reels_result(results, skipped=""):
    if skipped:
        console.print(f"[yellow]Scheduled slot skipped ({skipped}); no action needed.[/yellow]")
        return
    video_platforms = ("youtube", "instagram_reel", "pinterest")
    if not any(results.get(platform, False) for platform in video_platforms):
        console.print("[red]Scheduled video broadcast produced no published video. See the automation log for details.[/red]")
        raise SystemExit(1)

def _run_scheduled_reels(engine):
    if engine.daily_broadcast_cap_reached():
        _run_scheduled_reels_result({}, "daily_cap_reached")
        return
    _run_scheduled_reels_result(engine.run_studio_all())

def _run_scheduled_explainer(engine):
    result = engine.run_long_explainer_slot()
    if not result.get("published") and result.get("reason") != "not_alternate_day":
        console.print("[red]Scheduled explainer did not publish. See the automation log for details.[/red]")
        raise SystemExit(1)

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
            "generate-explainer",
            "generate-demo-short",
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
        custom_topic = {"title": args.topic} if args.topic else None
        engine.run_studio_all(topic=custom_topic)

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

    elif args.action == "generate-explainer":
        console.print("[bold magenta]⏳ Rendering long-form explainer only (no publishing)...[/bold magenta]")
        from src.technical_explainer import TechnicalExplainerStudio
        topic = {"title": args.topic} if args.topic else engine.get_fresh_topic(
            pillar="ai_systems", long_form=True
        )
        res = TechnicalExplainerStudio().generate_long_explainer_video(topic)
        console.print(
            f"[bold green]Explainer rendered: {res.get('duration')}s -> "
            f"{res.get('video_path')}[/bold green]"
        )

    elif args.action == "generate-demo-short":
        console.print("[bold cyan]🎬 Rendering next-generation demo short (no publishing)...[/bold cyan]")
        import re

        from src.short_script import build_short_script
        from src.short_script_ai import build_short_script_ai
        from src.storyboard_ai import build_storyboard_ai, deterministic_storyboard
        from src.voice import synthesize_performance, write_srt
        from src.short_visual_v3 import build_short_html_v3
        from src.video_generator import VideoGenerator

        topic = (
            {"title": args.topic, "pillar": "ai_systems"}
            if args.topic else engine.get_fresh_topic()
        )
        script = build_short_script_ai(topic) or build_short_script(topic)
        storyboard = build_storyboard_ai(topic, script) or deterministic_storyboard(topic, script)
        qa = script.get("qa", {})
        console.print(
            f"[dim]Script: {qa.get('word_count')} words, source={qa.get('source', 'fallback')}[/dim]"
        )
        console.print(
            "[dim]Visual recipes: "
            + ", ".join(b.get("template_id", "?") for b in storyboard["beats"])
            + f" ({storyboard.get('source', '?')})[/dim]"
        )
        for beat in script["beats"]:
            console.print(f"  [cyan]{beat['narration']}[/cyan]")

        gen = VideoGenerator()
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", script["title"].lower()).strip("_")[:35]
        work_dir = gen.output_dir / f"short_v3_{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)

        raw_mp3 = work_dir / "voice_raw.mp3"
        voice_result = None
        for voice in ("en-US-AvaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural"):
            try:
                voice_result = synthesize_performance(
                    script["narration"], str(raw_mp3), voice=voice
                )
                break
            except RuntimeError as exc:
                console.print(f"[yellow]Voice {voice} failed: {exc}[/yellow]")
        if voice_result is None:
            raise SystemExit("All narration voices failed")
        words = voice_result["words"]
        target = max(40.0, (words[-1]["end"] if words else 0.0) + 2.0)
        duration = gen._master_audio_from_mp3(
            str(raw_mp3), str(work_dir / "narration_master.wav"), target
        )

        html = build_short_html_v3(topic, script, storyboard, words, duration)
        (work_dir / "index.html").write_text(html, encoding="utf-8")
        (work_dir / "script.txt").write_text(script["narration"], encoding="utf-8")
        write_srt(words, str(work_dir / "subtitles.srt"))

        video_path = str(work_dir / f"short_v3_{slug}.mp4")
        ok = gen._render_hyperframes(work_dir, video_path)
        console.print(
            f"[bold green]Demo short: {video_path} ({duration:.1f}s, rendered={ok})[/bold green]"
        )
        if not ok:
            raise SystemExit(1)
        from scripts.qa_video import check_video

        vqa_ok, vqa_report = check_video(video_path)
        console.print(
            f"[cyan]QA: static {vqa_report.get('frozen_total_s')}s total / "
            f"{vqa_report.get('frozen_max_s')}s max, "
            f"black {vqa_report.get('black_total_s')}s, "
            f"loudness {vqa_report.get('loudness_lufs')} LUFS[/cyan]"
        )
        if not vqa_ok:
            for err in vqa_report.get("errors", []):
                console.print(f"[red]QA FAIL: {err}[/red]")
            raise SystemExit(1)

    elif args.action == "ig-diagnose":
        from scripts import ig_diagnose
        exit_code = ig_diagnose.main()
        console.print(f"[bold green]IG Diagnostic completed (exit code {exit_code})[/bold green]")

    elif args.action == "youtube-explainer":
        console.print(f"[bold magenta]🎬 Publishing 16:9 YouTube Long Explainer (Dry-run: {args.dry_run})...[/bold magenta]")
        custom_topic = {"title": args.topic} if args.topic else None
        engine.publish_youtube_explainer(topic=custom_topic)

    elif args.action == "long-explainer":
        console.print(f"[bold magenta]🎬 Running scheduled Long Explainer slot (Dry-run: {args.dry_run})...[/bold magenta]")
        _run_scheduled_explainer(engine)

    elif args.action == "threads":
        console.print(f"[bold magenta]🧵 Publishing to Threads (Dry-run: {args.dry_run})...[/bold magenta]")
        engine.publish_threads()

    elif args.action == "schedule-autopilot":
        console.print(f"[bold cyan]⏰ Running 4-Hour Autopilot Cycle (Dry-run: {args.dry_run})...[/bold cyan]")
        report = engine.schedule_autopilot()
        if not report.get("skipped"):
            _run_scheduled_reels_result(report.get("broadcast_results", {}))

    elif args.action == "schedule-reels-shorts":
        console.print(f"[bold cyan]⏰ Running scheduled Reels/Shorts...[/bold cyan]")
        _run_scheduled_reels(engine)

    elif args.action == "schedule-explainer":
        console.print(f"[bold magenta]⏰ Running scheduled Explainer...[/bold magenta]")
        _run_scheduled_explainer(engine)

    elif args.action == "schedule-today":
        from datetime import datetime
        current_time = datetime.now().strftime("%I:%M %p")
        console.print(f"[bold cyan]Current time: {current_time}[/bold cyan]")
        if current_time in ["05:15 PM", "07:15 PM"]:
            console.print(f"[bold green]Running scheduled Reels/Shorts publish...[/bold green]")
            _run_scheduled_reels(engine)
        elif current_time == "09:15 PM":
            console.print(f"[bold magenta]Running scheduled Explainer video publish...[/bold magenta]")
            _run_scheduled_explainer(engine)
        else:
            console.print(f"[yellow]Not a scheduled time. Current time: {current_time}[/yellow]")
            console.print(f"Scheduled times: 5:15 PM, 7:15 PM (Reels/Shorts), 9:15 PM (Explainer - alternate days)")

if __name__ == "__main__":
    main()