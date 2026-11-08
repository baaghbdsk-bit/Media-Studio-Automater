"""
Media Studio Automater Engine.
Autonomous High-Impact Video Studio for YouTube Shorts, Instagram Reels, Pinterest Video Pins, Threads, and YouTube Long Explainers.
Powered by Manim Community Edition for genuine 3Blue1Brown-style mathematical animations.
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

    def is_alternate_day_for_explainer(self) -> bool:
        """Determines if at least 2 days have passed since the last YouTube Explainer."""
        try:
            events = self.history.get("events", [])
            last_explainer = None
            for ev in reversed(events):
                if ev.get("type") == "explainer_video":
                    last_explainer = ev.get("time", "")
                    break
            if last_explainer:
                last_dt = datetime.strptime(last_explainer, "%Y-%m-%d %I:%M %p")
                days = (datetime.now() - last_dt).days
                return days >= 2
            return True
        except Exception:
            return True

    def run_studio_all(self, topic: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        Executes unified video studio production (9:16 Vertical Manim Short/Reel):
        1. Selects fresh high-signal breakthrough topic (or uses provided topic).
        2. Renders 1 to 3 minute vertical HD 1080x1920 Manim video with neural voiceover & synced captions.
        3. Broadcasts to YouTube Shorts, Instagram Reels (with Share to Threads), Pinterest, and Threads.
        """
        console.print("\n[bold cyan]🚀 Starting Media Studio Broadcast Cycle (Manim 9:16)...[/bold cyan]")
        start_time = time.time()
        results = {"youtube": False, "instagram_reel": False, "pinterest": False, "threads": False}

        if not topic:
            topic = self.get_fresh_topic()
        title = topic.get("title", "AI Architecture Breakthrough")
        summary = topic.get("summary", "")
        pro_tip = topic.get("pro_tip", "")
        console.print(f"[bold magenta]🎬 Studio Topic Selected: {title}[/bold magenta]")

        # 1. Render Technical Explainer Video (1 to 3 mins) with Manim fallback
        console.print("[cyan]⏳ Synthesizing Technical Explainer 3D video...[/cyan]")
        try:
            from src.technical_explainer import TechnicalExplainerStudio
            studio = TechnicalExplainerStudio(fps=24)
            p_res = studio.generate_explainer_video(topic)
            video_path = Path(p_res.get("video_path") or "")
            srt_path = Path(p_res.get("srt_path") or "") if p_res.get("srt_path") else None
        except Exception as p_err:
            console.print(f"[yellow]⚠️ Technical Explainer note: {p_err}. Falling back to Manim engine...[/yellow]")
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
                console.print("[yellow]⚠️ Instagram not authenticated. Set INSTAGRAM_COOKIES_BASE64.[/yellow]")
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
                console.print("[yellow]⚠️ Pinterest not authenticated. Set PINTEREST_COOKIES_BASE64.[/yellow]")
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

    def publish_youtube_explainer(self, topic: Optional[Dict[str, Any]] = None) -> bool:
        """
        Renders and publishes a full 16:9 Landscape long-form explainer to YouTube.
        Uses the premium motion-graphics engine with a Manim fallback.
        Includes chapter timestamps derived from the rendered runtime.
        """
        console.print("\n[bold magenta]🎬 Starting YouTube Long Explainer Production (16:9)...[/bold magenta]")
        if not topic:
            topic = self.get_fresh_topic()
        title = topic.get("title", "Frontier AI Architecture Deep-Dive")
        summary = topic.get("summary", "")
        pro_tip = topic.get("pro_tip", "")
        console.print(f"[bold cyan]Explainer Topic: {title}[/bold cyan]")

        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish 16:9 YouTube Explainer: {title}[/yellow]")
            return True

        try:
            from src.technical_explainer import TechnicalExplainerStudio
            studio = TechnicalExplainerStudio(fps=24)
            v_res = studio.generate_long_explainer_video(topic)
            vpath = Path(v_res.get("video_path") or "")
            srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None
            chapters = v_res.get("chapters", [])
        except Exception as long_err:
            console.print(
                f"[yellow]⚠️ Long-form motion engine note: {long_err}. "
                "Falling back to Manim engine...[/yellow]"
            )
            vid_gen = VideoGenerator()
            v_res = vid_gen.generate_dynamic_explainer(topic, dry_run=self.dry_run)
            vpath = Path(v_res.get("video_path") or "")
            srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None
            chapters = v_res.get("chapters", [
                "00:00 Introduction & The Scaling Dilemma",
                "01:45 Formal Mathematical Decomposition",
                "03:30 Dynamic Tensor Routing & SRAM Tiles",
                "05:15 Hardware Profiling & Compute Efficiency",
                "07:00 NeuBench Benchmarks & Production Rules"
            ])

        yt = YouTubeAutomater()
        if not yt.is_authenticated:
            console.print("[yellow]⚠️ YouTube not authenticated. Check YOUTUBE_TOKEN_BASE64.[/yellow]")
            return False

        chapters_text = "\n".join(chapters)
        desc = (
            f"⚡ Comprehensive Technical Breakdown: {title}\n\n"
            f"{summary}\n\n"
            f"📌 Timestamps & Chapters:\n{chapters_text}\n\n"
            f"💡 Production Engineering Rule:\n{pro_tip}\n\n"
            "📊 Compare live token economics & latency across 260+ models on NeuBench:\n"
            "https://app.neubench.workers.dev\n\n"
            "#AI #DeepLearning #MachineLearning #SystemArchitecture #Python #Algorithms"
        )

        res = yt.upload_short(
            video_path=str(vpath),
            title=f"{title}: Complete Technical Deep-Dive"[:95],
            description=desc,
            srt_path=str(srt_path) if srt_path and srt_path.exists() else None
        )

        if res:
            console.print(f"[bold green]✅ YouTube Long Explainer live: {res.get('url', '')}[/bold green]")
            self.record_topic(title)
            self.record_event("explainer_video", title, {"url": res.get("url")})
            return True
        return False

    def schedule_autopilot(self) -> Dict[str, Any]:
        """
        Primary 4-hour cron scheduler method:
        1. Selects exactly ONE fresh, non-duplicate topic.
        2. Produces and publishes the 9:16 Short/Reel/Pin/Thread broadcast.
        3. Permanently records the topic so the next cycle chooses a new topic.

        The 16:9 long-form video is handled by its own 7:30 pm IST slot
        (``run_long_explainer_slot``) so the two productions never compete
        for the same CI run.
        """
        report = {"broadcast_results": {}}
        console.print("\n[bold cyan]⏰ 4-Hour Autopilot Heartbeat Triggered...[/bold cyan]")

        # 1. Select ONE single fresh topic for this cycle
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Architecture Breakthrough")
        console.print(f"[bold magenta]🎬 Studio Unified Cycle Topic: {title}[/bold magenta]")

        # 2. Run the 9:16 short-form broadcast (YouTube Shorts, Reels, Pinterest, Threads)
        b_res = self.run_studio_all(topic=topic)
        report["broadcast_results"] = b_res

        # 3. Permanently record topic so it is NEVER duplicated in subsequent runs
        self.record_topic(title)
        return report

    def run_long_explainer_slot(self) -> Dict[str, Any]:
        """
        Daily 7:30 pm IST long-form slot.
        Publishes only on alternate days (>= 2 days since the last explainer).
        """
        console.print("\n[bold magenta]📅 Long-Form Explainer Slot Triggered...[/bold magenta]")
        if not self.is_alternate_day_for_explainer():
            console.print("[yellow]⏳ Not an alternate day - skipping long video slot.[/yellow]")
            return {"published": False, "reason": "not_alternate_day"}

        console.print("[bold magenta]✅ Alternate day confirmed - producing 16:9 long-form explainer...[/bold magenta]")
        topic = self.get_fresh_topic()
        ok = self.publish_youtube_explainer(topic=topic)
        return {"published": bool(ok)}

    def publish_youtube(self, topic: Optional[Dict[str, Any]] = None) -> bool:
        if not topic:
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
