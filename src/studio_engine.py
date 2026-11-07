"""
Media Studio Automater Engine.
Autonomous High-Impact Video Studio for YouTube Shorts, Instagram Reels, Pinterest Video Pins, and Threads.
"""
import sys
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from rich.console import Console

import config
from src.trend_hunter import TrendHunter
from src.ai_generator import AIGenerator
from src.video_generator import VideoGenerator
from src.youtube_automater import YouTubeAutomater
from src.instagram_automater import InstagramAutomater
from src.pinterest_automater import PinterestAutomater
from src.threads_automater import ThreadsAutomater

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

class StudioEngine:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.hunter = TrendHunter()
        self.ai = AIGenerator()
        self.history_file = config.BASE_DIR / "studio_history.json"
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"posted_topics": [], "events": []}

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[dim]History save note: {e}[/dim]")

    def get_fresh_topic(self) -> Dict[str, Any]:
        used = self.history.get("posted_topics", [])
        topic = self.hunter.get_dynamic_ai_topic(used_topics=used)
        return topic

    def record_topic(self, title: str):
        if title not in self.history.setdefault("posted_topics", []):
            self.history["posted_topics"].append(title)
        self._save_history()

    def record_event(self, event_type: str, title: str, details: Dict[str, Any]):
        event = {
            "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "type": event_type,
            "title": title,
            "details": details
        }
        self.history.setdefault("events", []).append(event)
        self._save_history()

    def run_studio_all(self) -> Dict[str, bool]:
        """
        Executes unified video studio production:
        1. Selects fresh high-signal AI breakthrough topic.
        2. Renders 50-58s vertical HD 1080x1920 video with neural voiceover & synced captions.
        3. Broadcasts to YouTube Shorts, Instagram Reels, Pinterest, and Threads.
        """
        console.print("\n[bold cyan]🚀 Starting Media Studio Broadcast Cycle...[/bold cyan]")
        start_time = time.time()
        results = {"youtube": False, "instagram_reel": False, "pinterest": False, "threads": False}

        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Architecture Breakthrough")
        summary = topic.get("summary", "")
        pro_tip = topic.get("pro_tip", "")
        console.print(f"[bold magenta]🎬 Studio Topic Selected: {title}[/bold magenta]")

        # 1. Render Video (for YouTube Shorts, Instagram Reels, Pinterest, & Threads)
        console.print("[cyan]⏳ Synthesizing 50-58s high-production vertical video...[/cyan]")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        video_path = Path(v_res.get("video_path") or "")
        srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None

        # 2. Publish to YouTube Shorts
        try:
            yt = YouTubeAutomater()
            yt_title = f"{title} Explained #Shorts"[:90]
            yt_desc = (
                f"⚡ {title}: {summary}\n\n"
                f"💡 Engineering Rule: {pro_tip}\n\n"
                "📊 Live 260+ model benchmarks: https://app.neubench.workers.dev\n\n"
                "#Shorts #AI #MachineLearning #DeepLearning #Python #SoftwareEngineering"
            )
            if self.dry_run:
                console.print(f"[yellow][DRY RUN] Would upload YouTube Short: {yt_title}[/yellow]")
                results["youtube"] = True
            elif not yt.is_authenticated:
                console.print("[yellow]⚠️ YouTube not authenticated. Check YOUTUBE_TOKEN_BASE64 or run 'python scripts/login_youtube.py'.[/yellow]")
            elif video_path.exists():
                console.print(f"[bold magenta]🎬 Uploading Short to YouTube: {yt_title}...[/bold magenta]")
                res = yt.upload_short(
                    video_path=str(video_path),
                    title=yt_title,
                    description=yt_desc,
                    srt_path=str(srt_path) if srt_path and srt_path.exists() else None
                )
                if res:
                    console.print(f"[bold green]✅ YouTube Short live: {res.get('url', '')}[/bold green]")
                    results["youtube"] = True
            else:
                console.print("[yellow]⚠️ YouTube Short skipped: video rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]YouTube error: {ex}[/red]")

        # 3. Publish to Instagram Reel (9:16 Uncropped) with 'Share to Threads' enabled
        try:
            ig = InstagramAutomater(headless=True, dry_run=self.dry_run)
            reel_caption = (
                f"⚡ {title}\n\n"
                f"{summary}\n\n"
                f"💡 Pro-Tip: {pro_tip}\n\n"
                "📊 Live 260+ model benchmarks: app.neubench.workers.dev\n\n"
                "#Reels #AI #MachineLearning #DeepLearning #Coding #Tech"
            )
            if self.dry_run:
                console.print(f"[yellow][DRY RUN] Would publish Instagram Reel: {title} (with Share to Threads)[/yellow]")
                results["instagram_reel"] = True
            elif not ig.is_session_available():
                console.print("[yellow]⚠️ Instagram not authenticated. Set INSTAGRAM_COOKIES_BASE64 or check instagram_session/cookies.json.[/yellow]")
            elif video_path.exists():
                console.print(f"[bold magenta]🎥 Publishing 9:16 Reel to Instagram (@neubench) & Threads...[/bold magenta]")
                r_ok, r_msg = ig.post_reel(str(video_path), reel_caption)
                if r_ok:
                    console.print("[bold green]✅ Instagram Reel published successfully![/bold green]")
                    results["instagram_reel"] = True
                else:
                    console.print(f"[yellow]Instagram Reel note: {r_msg}[/yellow]")
            else:
                console.print("[yellow]⚠️ Instagram Reel skipped: video rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]Instagram Reel error: {ex}[/red]")

        # 4. Publish to Pinterest (Vertical Video Pin)
        try:
            pin = PinterestAutomater(headless=True, dry_run=self.dry_run)
            p_desc = f"{title}\n\n{summary}\n\n💡 Pro-Tip: {pro_tip}\n\nLive AI Benchmarks: https://app.neubench.workers.dev\n\n#AI #Tech #MachineLearning #Engineering"
            if self.dry_run:
                console.print(f"[yellow][DRY RUN] Would publish Pinterest Video Pin: {title}[/yellow]")
                results["pinterest"] = True
            elif not pin.is_session_available():
                console.print("[yellow]⚠️ Pinterest not authenticated. Set PINTEREST_COOKIES_BASE64 or check pinterest_session/cookies.json.[/yellow]")
            elif video_path.exists():
                console.print(f"[bold magenta]📌 Publishing Video Pin to Pinterest: {title[:50]}...[/bold magenta]")
                p_ok, p_msg = pin.create_pin(
                    image_path=str(video_path),
                    title=f"{title} • AI Breakdown"[:80],
                    description=p_desc,
                    link="https://app.neubench.workers.dev"
                )
                if p_ok:
                    console.print("[bold green]✅ Pinterest Pin published![/bold green]")
                    results["pinterest"] = True
                else:
                    console.print(f"[yellow]Pinterest note: {p_msg}[/yellow]")
            else:
                console.print("[yellow]⚠️ Pinterest skipped: video rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]Pinterest error: {ex}[/red]")

        # 5. Dedicated Broadcast to Threads (Failsafe alongside Instagram crosspost)
        try:
            threads = ThreadsAutomater(headless=True, dry_run=self.dry_run)
            threads_text = (
                f"🧠 {title}\n\n"
                f"{summary}\n\n"
                f"💡 Engineering Rule: {pro_tip}\n\n"
                "📊 Live 260+ model benchmarks: https://app.neubench.workers.dev\n\n"
                "#AI #Tech #Engineering"
            )
            if self.dry_run:
                console.print(f"[yellow][DRY RUN] Would publish Threads take: {title}[/yellow]")
                results["threads"] = True
            elif not threads.is_session_available():
                console.print("[dim]Threads session not configured directly; relying on Instagram 'Share to Threads'.[/dim]")
            else:
                console.print(f"[bold magenta]🧵 Publishing to Threads...[/bold magenta]")
                t_ok, t_msg = threads.post(threads_text)
                if t_ok:
                    console.print("[bold green]✅ Threads post published![/bold green]")
                    results["threads"] = True
                else:
                    console.print(f"[dim]Threads note: {t_msg}[/dim]")
        except Exception as ex:
            console.print(f"[dim]Threads broadcast note: {ex}[/dim]")

        # Record success
        if any(results.values()):
            self.record_topic(title)
            self.record_event("video_broadcast", title, results)

        duration = round(time.time() - start_time, 1)
        console.print(f"\n[bold green]🏁 Studio Broadcast Complete in {duration}s! Results: {results}[/bold green]\n")
        return results

    def publish_youtube(self) -> bool:
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        vpath = Path(v_res.get("video_path") or "")
        srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None
        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish YouTube Short: {title}[/yellow]")
            return True
        yt = YouTubeAutomater()
        if not yt.is_authenticated:
            console.print("[yellow]YouTube not authenticated.[/yellow]")
            return False
        res = yt.upload_short(
            video_path=str(vpath),
            title=f"{title} Explained #Shorts"[:90],
            description=f"⚡ {title}: {topic.get('summary', '')}\n\n💡 Pro-Tip: {topic.get('pro_tip', '')}\n\n#Shorts #AI",
            srt_path=str(srt_path) if srt_path and srt_path.exists() else None
        )
        if res:
            console.print(f"[bold green]✅ YouTube Short live: {res.get('url', '')}[/bold green]")
            self.record_topic(title)
            self.record_event("youtube_short", title, {"url": res.get("url")})
            return True
        return False

    def publish_instagram_reel(self) -> bool:
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        vpath = Path(v_res.get("video_path") or "")
        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish Instagram Reel: {title}[/yellow]")
            return True
        ig = InstagramAutomater(headless=True, dry_run=self.dry_run)
        caption = f"⚡ {title}\n\n{topic.get('summary', '')}\n\n💡 {topic.get('pro_tip', '')}\n\n#Reels #AI"
        ok, msg = ig.post_reel(str(vpath), caption)
        if ok:
            console.print(f"[bold green]✅ Instagram Reel published![/bold green]")
            self.record_topic(title)
            self.record_event("instagram_reel", title, {"msg": msg})
        else:
            console.print(f"[yellow]Instagram Reel note: {msg}[/yellow]")
        return ok

    def publish_pinterest(self) -> bool:
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        vpath = Path(v_res.get("video_path") or "")
        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish Pinterest Pin: {title}[/yellow]")
            return True
        pin = PinterestAutomater(headless=True, dry_run=self.dry_run)
        desc = f"{title}\n\n{topic.get('summary', '')}\n\n#AI #Tech"
        ok, msg = pin.create_pin(image_path=str(vpath), title=f"{title} • AI Breakdown"[:80], description=desc)
        if ok:
            console.print("[bold green]✅ Pinterest Pin published![/bold green]")
            self.record_topic(title)
            self.record_event("pinterest_pin", title, {"msg": msg})
        else:
            console.print(f"[yellow]Pinterest note: {msg}[/yellow]")
        return ok

    def publish_threads(self) -> bool:
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish Threads take: {title}[/yellow]")
            return True
        threads = ThreadsAutomater(headless=True, dry_run=self.dry_run)
        text = f"🧠 {title}\n\n{topic.get('summary', '')}\n\n💡 {topic.get('pro_tip', '')}\n\nhttps://app.neubench.workers.dev"
        ok, msg = threads.post(text)
        if ok:
            console.print("[bold green]✅ Threads post published![/bold green]")
            self.record_topic(title)
            self.record_event("threads_post", title, {"msg": msg})
        else:
            console.print(f"[yellow]Threads note: {msg}[/yellow]")
        return ok
