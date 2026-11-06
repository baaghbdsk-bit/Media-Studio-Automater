"""
Media Studio Automater Engine.
Dedicated High-Impact Visual Studio for YouTube Shorts, Instagram Reels, Instagram Carousels, and Pinterest Pins.
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
from src.instagram_automater import InstagramAutomater
from src.pinterest_automater import PinterestAutomater

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
        self.history.setdefault("posted_topics", []).append(title)
        self._save_history()

    def run_studio_all(self) -> Dict[str, bool]:
        """
        Executes unified studio production:
        1. Selects fresh high-signal AI breakthrough topic.
        2. Renders 50-58s vertical HD 1080x1920 video with neural voiceover & synced captions.
        3. Renders 5-slide dynamic cheatsheet carousel (1080x1350).
        4. Broadcasts to YouTube Shorts, Instagram Reels, Instagram Carousel, and Pinterest.
        """
        console.print("\n[bold cyan]🚀 Starting Media Studio Broadcast Cycle...[/bold cyan]")
        start_time = time.time()
        results = {"youtube": False, "instagram_reel": False, "instagram_carousel": False, "pinterest": False}

        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Architecture Breakthrough")
        summary = topic.get("summary", "")
        pro_tip = topic.get("pro_tip", "")
        console.print(f"[bold magenta]🎬 Studio Topic Selected: {title}[/bold magenta]")

        # 1. Render Video (for YouTube Shorts & Instagram Reels)
        console.print("[cyan]⏳ Synthesizing 50-58s high-production vertical video...[/cyan]")
        vid_gen = VideoGenerator()
        v_res = vid_gen.generate_dynamic_short(topic, dry_run=self.dry_run)
        video_path = Path(v_res.get("video_path") or "")
        srt_path = Path(v_res.get("srt_path") or "") if v_res.get("srt_path") else None

        

        # 3. Publish to YouTube Shorts
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
                console.print("[yellow]⚠️ YouTube not authenticated. Run 'python main.py login-youtube'.[/yellow]")
            elif video_path.exists():
                console.print(f"[bold magenta]🎬 Uploading Short to YouTube: {yt_title}...[/bold magenta]")
                res = yt.upload_short(video_path=str(video_path), title=yt_title, description=yt_desc, srt_path=str(srt_path) if srt_path and srt_path.exists() else None)
                if res:
                    console.print(f"[bold green]✅ YouTube Short live: {res.get('url', '')}[/bold green]")
                    results["youtube"] = True
            else:
                console.print("[yellow]⚠️ YouTube Short skipped: video rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]YouTube error: {ex}[/red]")

        # 4. Publish to Instagram Reel (9:16 Uncropped)
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
                console.print(f"[yellow][DRY RUN] Would publish Instagram Reel: {title}[/yellow]")
                results["instagram_reel"] = True
            elif not ig.is_session_available():
                console.print("[yellow]⚠️ Instagram not authenticated. Run 'python main.py login-instagram'.[/yellow]")
            elif video_path.exists():
                console.print(f"[bold magenta]🎥 Publishing 9:16 Reel to Instagram (@neubench)...[/bold magenta]")
                r_ok, r_msg = ig.post_reel(str(video_path), reel_caption)
                if r_ok:
                    console.print("[bold green]✅ Instagram Reel published![/bold green]")
                    results["instagram_reel"] = True
                else:
                    console.print(f"[yellow]Instagram Reel note: {r_msg}[/yellow]")
            else:
                console.print("[yellow]⚠️ Instagram Reel skipped: video rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]Instagram Reel error: {ex}[/red]")

        # 5. Publish to Instagram Carousel (Original 4:5 Uncropped 5-Slide Cheatsheet)
        try:
            ig = InstagramAutomater(headless=True, dry_run=self.dry_run)
            carousel_caption = (
                f"🧠 {title} • Engineering Cheatsheet\n\n"
                f"⚡ {summary}\n\n"
                "Swipe through the 1-page breakdown ➡️\n\n"
                f"💡 Pro-Tip: {pro_tip}\n\n"
                "📌 Save this post for your revision!\n"
                "📊 Live 260+ model benchmarks: app.neubench.workers.dev\n\n"
                "#AI #MachineLearning #AIEngineering #Coding #Developers #Tech"
            )
            if self.dry_run:
                console.print(f"[yellow][DRY RUN] Would publish Instagram Carousel ({len(valid_slides)} slides)[/yellow]")
                results["instagram_carousel"] = True
            elif not ig.is_session_available():
                console.print("[yellow]⚠️ Instagram not authenticated. Run 'python main.py login-instagram'.[/yellow]")
            elif valid_slides:
                console.print(f"[bold magenta]📸 Publishing 5-Slide Carousel to Instagram (@neubench)...[/bold magenta]")
                c_ok, c_msg = ig.post_carousel(valid_slides, carousel_caption)
                if c_ok:
                    console.print("[bold green]✅ Instagram Carousel published![/bold green]")
                    results["instagram_carousel"] = True
                else:
                    console.print(f"[yellow]Instagram Carousel note: {c_msg}[/yellow]")
            else:
                console.print("[yellow]⚠️ Instagram Carousel skipped: slides rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]Instagram Carousel error: {ex}[/red]")

        # 6. Publish to Pinterest (Multi-Slide Carousel Pin)
        try:
            pin = PinterestAutomater(headless=True, dry_run=self.dry_run)
            p_desc = f"{title}\n\n{summary}\n\n💡 Pro-Tip: {pro_tip}\n\nLive AI Benchmarks: https://app.neubench.workers.dev\n\n#AI #Tech #MachineLearning #Engineering"
            if self.dry_run:
                console.print(f"[yellow][DRY RUN] Would publish Pinterest Carousel Pin: {title}[/yellow]")
                results["pinterest"] = True
            elif not pin.is_session_available():
                console.print("[yellow]⚠️ Pinterest not authenticated. Run 'python main.py login-pinterest'.[/yellow]")
            elif valid_slides:
                console.print(f"[bold magenta]📌 Publishing {len(valid_slides)}-Slide Pin to Pinterest: {title[:50]}...[/bold magenta]")
                p_ok, p_msg = pin.create_pin(
                    image_path=valid_slides,
                    title=f"{title} • AI Cheatsheet"[:80],
                    description=p_desc,
                    link="https://app.neubench.workers.dev"
                )
                if p_ok:
                    console.print("[bold green]✅ Pinterest Pin published![/bold green]")
                    results["pinterest"] = True
                else:
                    console.print(f"[yellow]Pinterest note: {p_msg}[/yellow]")
            else:
                console.print("[yellow]⚠️ Pinterest skipped: slides rendering failed.[/yellow]")
        except Exception as ex:
            console.print(f"[red]Pinterest error: {ex}[/red]")

        # Record success
        if any(results.values()):
            self.record_topic(title)

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
        else:
            console.print(f"[yellow]Instagram Reel note: {msg}[/yellow]")
        return ok

    def publish_instagram_carousel(self) -> bool:
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        gen = InstagramCarouselGenerator()
        slides = gen.generate_dynamic_carousel(topic)
        valid = [str(p) for p in slides if Path(p).exists()] if slides else []
        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish Instagram Carousel: {title}[/yellow]")
            return True
        ig = InstagramAutomater(headless=True, dry_run=self.dry_run)
        caption = f"🧠 {title} • Engineering Cheatsheet\n\n{topic.get('summary', '')}\n\n#AI #Coding"
        ok, msg = ig.post_carousel(valid, caption)
        if ok:
            console.print(f"[bold green]✅ Instagram Carousel published![/bold green]")
            self.record_topic(title)
        else:
            console.print(f"[yellow]Instagram Carousel note: {msg}[/yellow]")
        return ok

    def publish_pinterest(self) -> bool:
        topic = self.get_fresh_topic()
        title = topic.get("title", "AI Concept")
        # No carousel slides - publish single pin with title/description
        if self.dry_run:
            console.print(f"[yellow][DRY RUN] Would publish Pinterest Pin: {title}[/yellow]")
            return True
        pin = PinterestAutomater(headless=True, dry_run=self.dry_run)
        # Since we removed the carousel section, use no image or a placeholder
        desc = f"{title}\n\n{topic.get('summary', '')}\n\n#AI #Tech"
        ok, msg = pin.create_pin(image_path=None, title=f"{title} • AI Cheatsheet"[:80], description=desc)
        if ok:
            console.print("[bold green]✅ Pinterest Pin published![/bold green]")
            self.record_topic(title)
        else:
            console.print(f"[yellow]Pinterest note: {msg}[/yellow]")
        return ok

    
