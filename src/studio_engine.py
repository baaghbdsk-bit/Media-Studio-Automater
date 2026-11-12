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
from datetime import datetime, timezone, timedelta
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
    YOUTUBE_DAILY_UNITS = 9000
    YOUTUBE_UPLOAD_UNITS = 2000

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run or (os.environ.get("DRY_RUN", "").strip().lower() in ("true", "1"))
        self.hunter = TrendHunter()
        self.ai = AIGenerator()
        self.history_file = config.BASE_DIR / "studio_history.json"
        self.history = self._load_history()
        self._migrate_history()

    def _load_history(self) -> Dict[str, Any]:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {"posted_topics": [], "topic_log": [], "events": []}

    def _migrate_history(self):
        """Seed the timestamped topic log from the legacy posted_topics list.

        Legacy entries get a migration timestamp so they block repeats for one
        month and then age out instead of blocking the topic forever.
        """
        log = self.history.get("topic_log")
        if not isinstance(log, list):
            log = []
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        known = set()
        for entry in log:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "")
            known.add(title)
            if title and not entry.get("time"):
                entry["time"] = now_iso
        for title in self.history.get("posted_topics", []):
            if title and title not in known:
                log.append({"title": title, "series": "", "time": now_iso, "legacy": True})
                known.add(title)
        self.history["topic_log"] = log[-600:]

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[dim]History save note: {e}[/dim]")

    def _recent_entries(self) -> List[Dict[str, Any]]:
        from src import topic_memory

        log = [e for e in self.history.get("topic_log", []) if isinstance(e, dict)]
        if not log:
            return [{"title": t, "series": "", "time": ""}
                    for t in self.history.get("posted_topics", []) if t]
        return topic_memory.recent(log)

    def get_fresh_topic(self, audience: str = "beginner",
                        pillar: str = "NEWS",
                        long_form: bool = False) -> Dict[str, Any]:
        """Pick a topic that has not appeared in the last 30 days."""
        from src import topic_memory

        entries = self._recent_entries()
        used = topic_memory.recent_titles(entries)
        if not used:
            used = list(self.history.get("posted_topics", []))
        exclude_series = topic_memory.recent_series(entries)

        for attempt in range(3):
            topic = self.hunter.get_dynamic_ai_topic(
                used_topics=used,
                audience=audience,
                pillar=pillar,
                exclude_series=exclude_series,
                long_form=long_form,
            )
            if not topic_memory.is_duplicate(topic, entries):
                return topic
            title = topic.get("title", "")
            console.print(
                f"[yellow]Duplicate topic rejected ({attempt + 1}/3): {title}[/yellow]")
            if title and title not in used:
                used.append(title)

        # Deterministic last resort: the curriculum bank will still avoid titles.
        return self.hunter.get_dynamic_ai_topic(
            used_topics=used,
            audience=audience,
            pillar=pillar,
            exclude_series=exclude_series,
            long_form=long_form,
        )

    def record_topic(self, title: str, series: str = "", audience: str = "",
                     pillar: str = "", long_form: bool = False):
        if not title:
            return
        entry = {
            "title": title,
            "series": series,
            "audience": audience,
            "pillar": pillar,
            "long_form": bool(long_form),
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        log = self.history.setdefault("topic_log", [])
        log.append(entry)
        self.history["topic_log"] = log[-600:]

        posted = self.history.setdefault("posted_topics", [])
        if title not in posted:
            posted.append(title)
        self.history["posted_topics"] = posted[-300:]
        self._save_history()

    def record_event(self, event_type: str, title: str, details: Dict[str, Any]):
        event = {
            "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "type": event_type,
            "title": title,
            "details": details
        }
        events = self.history.setdefault("events", [])
        events.append(event)
        self.history["events"] = events[-500:]
        self._save_history()

    def is_alternate_day_for_explainer(self) -> Optional[bool]:
        """Determines if at least 2 days have passed since the last YouTube Explainer."""
        events = self.history.get("events", [])
        if not isinstance(events, list):
            console.print("[red]Explainer schedule skipped: event history is not a list.[/red]")
            return None

        for event in reversed(events):
            if not isinstance(event, dict) or event.get("type") != "explainer_video":
                continue
            timestamp = event.get("time")
            try:
                last_date = datetime.strptime(timestamp, "%Y-%m-%d %I:%M %p").date()
            except (TypeError, ValueError):
                console.print("[red]Explainer schedule skipped: latest explainer timestamp is invalid.[/red]")
                return None
            days = (self._ist_now().date() - last_date).days
            return days >= 2
        return True

    @staticmethod
    def _ist_now() -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

    def _slot_context(self, long_form: bool = False):
        """Deterministic audience/pillar rotation for the current IST slot."""
        now = self._ist_now()
        if long_form:
            pillars = ("foundations", "ai_systems", "engineering")
            idx = now.toordinal() % 3
            return "beginner", pillars[idx]
        # Every short-form slot is news-first; the ELI5 bank is only a fallback.
        return "beginner", "NEWS"

    def _is_evening_short_slot(self) -> bool:
        return 18 <= self._ist_now().hour < 21

    def _youtube_units_used(self) -> int:
        today = self._ist_now().date().isoformat()
        return int((self.history.get("youtube_units") or {}).get(today, 0))

    def _youtube_budget_left(self) -> int:
        return self.YOUTUBE_DAILY_UNITS - self._youtube_units_used()

    def _youtube_uploads_today(self) -> int:
        return self._youtube_units_used() // self.YOUTUBE_UPLOAD_UNITS

    def _record_youtube_upload(self):
        today = self._ist_now().date().isoformat()
        units = self.history.setdefault("youtube_units", {})
        units[today] = int(units.get(today, 0)) + self.YOUTUBE_UPLOAD_UNITS
        cutoff = (self._ist_now().date() - timedelta(days=7)).isoformat()
        self.history["youtube_units"] = {d: v for d, v in units.items() if d >= cutoff}
        self._save_history()

    @staticmethod
    def _rendered_video_path(render_result: Dict[str, Any], label: str) -> Optional[Path]:
        raw_path = render_result.get("video_path")
        if not raw_path:
            console.print(f"[red]⚠️ {label} skipped: video rendering returned no output file.[/red]")
            return None

        video_path = Path(raw_path)
        if not video_path.is_file():
            console.print(f"[red]⚠️ {label} skipped: rendered video is not a file: {video_path}[/red]")
            return None
        return video_path

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

        # 1. Render Technical Explainer Video (9:16 Shorts/Reel) with Cinematic Engine
        console.print("[cyan]⏳ Synthesizing Technical Explainer 9:16 video (HyperFrames + Edge-TTS)...[/cyan]")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        video_path = self._rendered_video_path(v_res, "Video broadcast")
        if video_path is None:
            duration = round(time.time() - start_time, 1)
            console.print(f"\n[bold red]❌ Studio Broadcast stopped after {duration}s: no rendered video.[/bold red]\n")
            return results
        srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None

        # 2. Publish to YouTube Shorts
        try:
            yt = YouTubeAutomater()
            is_news = str(topic.get("pillar") or "").upper() == "NEWS"
            yt_title = (f"{title} #Shorts" if is_news else f"{title} Explained #Shorts")[:90]
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
                console.print("[yellow]�s��,? YouTube not authenticated. Check YOUTUBE_TOKEN_BASE64 or run 'python scripts/login_youtube.py'.[/yellow]")
            elif self._youtube_uploads_today() >= int(config.CAPS_PER_PLATFORM.get("youtube_shorts", 2)):
                console.print(
                    "[yellow]YouTube daily Short cap reached "
                    f"({config.CAPS_PER_PLATFORM.get('youtube_shorts', 2)}/day); skipping upload.[/yellow]")
            elif self._youtube_budget_left() < self.YOUTUBE_UPLOAD_UNITS:
                console.print(
                    "[yellow]🛡️ YouTube quota guard: daily budget exhausted, "
                    "skipping the short upload.[/yellow]")
            elif video_path.is_file():
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
                    self._record_youtube_upload()
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
            elif video_path.is_file():
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
            elif video_path.is_file():
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

        # Record success (never mutate state during a dry run)
        if any(results.values()) and not self.dry_run:
            self.record_topic(
                title,
                series=str(topic.get("series") or ""),
                audience=str(topic.get("audience") or ""),
                pillar=str(topic.get("pillar") or ""),
            )
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
            topic = self.get_fresh_topic(pillar="ai_systems")
        title = topic.get("title", "Frontier AI Architecture Deep-Dive")
        summary = topic.get("summary", "")
        pro_tip = topic.get("pro_tip", "")
        console.print(f"[bold cyan]Explainer Topic: {title}[/bold cyan]")

        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish 16:9 YouTube Explainer: {title}[/yellow]")
            return True

        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_explainer(topic, dry_run=self.dry_run)
        vpath = self._rendered_video_path(v_res, "YouTube explainer")
        if vpath is None:
            return False
        srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None
        chapters = v_res.get("chapters", [
            "00:00 Introduction & Architectural Context",
            "01:45 Formal Mathematical Decomposition",
            "03:30 Dynamic Tensor Routing & Memory Hierarchy",
            "05:15 Hardware Profiling & Compute Efficiency",
            "07:00 Production Rules & Benchmarks"
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

        if self._youtube_budget_left() < self.YOUTUBE_UPLOAD_UNITS:
            console.print(
                "[yellow]🛡️ YouTube quota guard: daily budget exhausted, "
                "skipping the long-form upload.[/yellow]")
            return False

        res = yt.upload_short(
            video_path=str(vpath),
            title=f"{title}: Complete Technical Deep-Dive"[:95],
            description=desc,
            srt_path=str(srt_path) if srt_path and srt_path.exists() else None
        )

        if res:
            console.print(f"[bold green]✅ YouTube Long Explainer live: {res.get('url', '')}[/bold green]")
            self._record_youtube_upload()
            self.record_topic(
                title,
                series=str(topic.get("series") or ""),
                audience=str(topic.get("audience") or ""),
                pillar=str(topic.get("pillar") or ""),
                long_form=True,
            )
            self.record_event("explainer_video", title, {"url": res.get("url")})
            return True
        return False

    def schedule_autopilot(self) -> Dict[str, Any]:
        """
        Scheduled short-form method (08:30 / 12:30 / 17:30 / 19:30 IST):
        1. Selects exactly ONE fresh, non-duplicate topic for this slot.
        2. Produces and publishes the 9:16 Short/Reel/Pin/Thread broadcast.
        3. Permanently records the topic so the next cycle chooses a new one.

        The 16:9 long-form video runs in its own 21:30 IST slot
        (``run_long_explainer_slot``). On long-form days the 19:30 short is
        skipped so the daily YouTube API quota can absorb the long upload.
        """
        report: Dict[str, Any] = {"broadcast_results": {}}
        console.print("\n[bold cyan]⏰ Scheduled Autopilot Heartbeat Triggered...[/bold cyan]")

        # Quota guard: on long-form days the evening short is skipped ONLY IF
        # remaining daily budget is insufficient for both this short and tonight's long form.
        if (
            self._is_evening_short_slot()
            and self.is_alternate_day_for_explainer()
            and (self._youtube_budget_left() < (self.YOUTUBE_UPLOAD_UNITS * 2))
        ):
            console.print(
                "[yellow]🛡️ 19:30 IST short skipped: quota reserved for tonight's "
                "21:30 IST long-form upload.[/yellow]"
            )
            if not self.dry_run:
                self.record_event(
                    "slot_skipped", "quota_reserved_for_long_form",
                    {"slot": "19:30 IST"},
                )
            return {
                "broadcast_results": {},
                "skipped": "quota_reserved_for_long_form",
            }

        # 1. Select ONE fresh topic levelled for this slot's audience/pillar
        audience, pillar = self._slot_context()
        topic = self.get_fresh_topic(audience=audience, pillar=pillar)
        title = topic.get("title", "AI Architecture Breakthrough")
        console.print(
            f"[bold magenta]🎬 {audience}/{pillar} topic: {title}[/bold magenta]")

        # 2. Run the 9:16 short-form broadcast (YouTube Shorts, Reels, Pinterest, Threads)
        b_res = self.run_studio_all(topic=topic)
        report["broadcast_results"] = b_res
        report["audience"] = audience
        report["pillar"] = pillar
        return report

    def run_long_explainer_slot(self) -> Dict[str, Any]:
        """
        Daily 7:30 pm IST long-form slot.
        Publishes only on alternate days (>= 2 days since the last explainer).
        """
        console.print("\n[bold magenta]📅 Long-Form Explainer Slot Triggered...[/bold magenta]")
        alternate_day = self.is_alternate_day_for_explainer()
        if alternate_day is None:
            return {"published": False, "reason": "invalid_history"}
        if not alternate_day:
            console.print("[yellow]⏳ Not an alternate day - skipping long video slot.[/yellow]")
            return {"published": False, "reason": "not_alternate_day"}

        console.print("[bold magenta]✅ Alternate day confirmed - producing 16:9 long-form explainer...[/bold magenta]")
        audience, pillar = self._slot_context(long_form=True)
        topic = self.get_fresh_topic(audience=audience, pillar=pillar, long_form=True)
        ok = self.publish_youtube_explainer(topic=topic)
        return {"published": bool(ok), "audience": audience, "pillar": pillar}

    def publish_youtube(self, topic: Optional[Dict[str, Any]] = None) -> bool:
        if not topic:
            topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        vpath = self._rendered_video_path(v_res, "YouTube Short")
        if vpath is None:
            return False
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
            title=(f"{title} #Shorts" if str(topic.get("pillar") or "").upper() == "NEWS" else f"{title} Explained #Shorts")[:90],
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
        vpath = self._rendered_video_path(v_res, "Instagram Reel")
        if vpath is None:
            return False
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
        vpath = self._rendered_video_path(v_res, "Pinterest video pin")
        if vpath is None:
            return False
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
