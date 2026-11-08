"""
Technical Explainer Studio Engine.

Autonomous premium explainer studio for YouTube Shorts, Instagram Reels,
Pinterest and long-form explainers:
- Editorial SVG motion-graphics direction (cyan / amber / red / emerald)
- Scene-accurate neural voiceover with a quiet cinematic ambient bed
- Deterministic headless-Chromium render piped straight into FFmpeg
- 1080x1920 vertical HD shorts and 1920x1080 landscape long-form
- Readable synced captions and YouTube chapter markers
- 100% free and open source, runs on a CPU-only GitHub Actions runner
"""
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .storyboard_planner import ExplainerStoryboardPlanner
from .explainer_renderer import ExplainerRenderer
from .narration_builder import SceneNarrationBuilder


class TechnicalExplainerStudio:
    LONG_FPS = 20
    LONG_WIDTH = 1920
    LONG_HEIGHT = 1080

    def __init__(self, output_root: Optional[Path] = None, fps: int = 24):
        self.output_root = Path(output_root) if output_root else Path("generated_visuals/videos")
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.planner = ExplainerStoryboardPlanner()
        self.renderer = ExplainerRenderer(fps=self.fps)
        self.narration = SceneNarrationBuilder(fps=self.fps)

    def generate_explainer_video(
        self,
        topic_data: Dict[str, Any],
        custom_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end explainer production:
        1. Plan the multi-act technical storyboard
        2. Synthesize per-scene narration (exact sync) + ambient bed
        3. Render the motion-graphics studio frame-by-frame -> FFmpeg
        4. Package the MP4, SRT and telemetry
        """
        title = topic_data.get("title", "Technical Architecture Breakdown")
        slug = custom_slug or re.sub(r"[^\w\-]", "_", title.lower())[:35]
        work_dir = self.output_root / f"explainer_{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 65, flush=True)
        print(f"[TechnicalExplainer] Generating: '{title}'", flush=True)
        print(f"[TechnicalExplainer] Work Directory: {work_dir}", flush=True)
        print("=" * 65, flush=True)

        # 1. Storyboard
        print("[TechnicalExplainer] Planning the technical narrative...", flush=True)
        storyboard = self.planner.plan_storyboard(topic_data)

        # 2. Scene-accurate narration + ambient bed
        print("[TechnicalExplainer] Synthesizing scene-accurate voiceover...", flush=True)
        audio_result = self.narration.build(storyboard, work_dir)
        audio_path = Path(audio_result["audio_path"])
        visemes = audio_result["visemes"]

        # 3. Render
        final_mp4 = work_dir / f"explainer_{slug}.mp4"
        render_result = self.renderer.render(
            storyboard=storyboard,
            visemes=visemes,
            audio_path=audio_path,
            output_path=final_mp4,
            work_dir=work_dir,
        )

        # 4. Package
        result = {
            "title": title,
            "category": storyboard.get("category", "SYSTEMS"),
            "video_path": str(final_mp4),
            "srt_path": render_result.get("srt_path"),
            "thumbnail_path": render_result.get("thumbnail_path"),
            "audio_path": str(audio_path),
            "duration": render_result.get("duration"),
            "fps": self.fps,
            "frames": render_result.get("frames"),
            "file_size_mb": render_result.get("file_size_mb"),
            "audience": topic_data.get("audience", "beginner"),
            "pillar": topic_data.get("pillar", ""),
            "storyboard": storyboard,
            "format": "1080x1920 (9:16 Vertical HD)",
            "visual_identity": "Editorial motion-graphics (cyan / amber / red / emerald)",
            "scenes_count": len(storyboard.get("scenes", [])),
        }

        print("[TechnicalExplainer] SUCCESS! Explainer video complete!", flush=True)
        print(f"   Video File: {final_mp4} ({result['file_size_mb']} MB, {result['duration']:.1f}s)", flush=True)
        print(f"   Subtitles:  {result['srt_path']}", flush=True)
        return result

    def generate_long_explainer_video(
        self,
        topic_data: Dict[str, Any],
        custom_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end 16:9 long-form production (same premium engine, landscape
        composition, 12 acts). Uses a slightly lower frame rate so a 4-5 minute
        explainer still fits comfortably inside a CPU-only CI budget.
        """
        title = topic_data.get("title", "Frontier AI Architecture")
        slug = custom_slug or re.sub(r"[^\w\-]", "_", title.lower())[:35]
        work_dir = self.output_root / f"explainer_long_{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 65, flush=True)
        print(f"[TechnicalExplainer] Generating 16:9 long-form: '{title}'", flush=True)
        print(f"[TechnicalExplainer] Work Directory: {work_dir}", flush=True)
        print("=" * 65, flush=True)

        # 1. Long-form storyboard (12 acts)
        print("[TechnicalExplainer] Planning the long-form narrative...", flush=True)
        storyboard = self.planner.plan_long_storyboard(topic_data)

        # 2. Scene-accurate narration + ambient bed
        print("[TechnicalExplainer] Synthesizing scene-accurate voiceover...", flush=True)
        narration = SceneNarrationBuilder(fps=self.LONG_FPS)
        audio_result = narration.build(storyboard, work_dir)
        audio_path = Path(audio_result["audio_path"])
        visemes = audio_result["visemes"]

        # 3. Landscape render
        final_mp4 = work_dir / f"explainer_long_{slug}.mp4"
        renderer = ExplainerRenderer(
            fps=self.LONG_FPS,
            width=self.LONG_WIDTH,
            height=self.LONG_HEIGHT,
            orientation="landscape",
        )
        render_result = renderer.render(
            storyboard=storyboard,
            visemes=visemes,
            audio_path=audio_path,
            output_path=final_mp4,
            work_dir=work_dir,
        )

        chapters = self._build_chapters(storyboard, render_result.get("duration", 0.0))

        result = {
            "title": title,
            "category": storyboard.get("category", "SYSTEMS"),
            "video_path": str(final_mp4),
            "srt_path": render_result.get("srt_path"),
            "thumbnail_path": render_result.get("thumbnail_path"),
            "audio_path": str(audio_path),
            "duration": render_result.get("duration"),
            "fps": self.LONG_FPS,
            "frames": render_result.get("frames"),
            "file_size_mb": render_result.get("file_size_mb"),
            "audience": topic_data.get("audience", "beginner"),
            "pillar": topic_data.get("pillar", ""),
            "storyboard": storyboard,
            "format": f"{self.LONG_WIDTH}x{self.LONG_HEIGHT} (16:9 Landscape HD)",
            "visual_identity": "Editorial motion-graphics (cyan / amber / red / emerald)",
            "scenes_count": len(storyboard.get("scenes", [])),
            "chapters": chapters,
        }

        print("[TechnicalExplainer] SUCCESS! Long-form explainer complete!", flush=True)
        print(
            f"   Video File: {final_mp4} "
            f"({result['file_size_mb']} MB, {result['duration']:.1f}s)",
            flush=True,
        )
        print(f"   Subtitles:  {result['srt_path']}", flush=True)
        return result

    @staticmethod
    def _format_ts(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _build_chapters(self, storyboard: Dict[str, Any], duration: float) -> list:
        """Topic-aware chapter markers at roughly quarter points of the acts."""
        scenes = storyboard.get("scenes", [])
        if not scenes:
            return []
        group = max(1, len(scenes) // 4)
        chapters = []
        for idx in (0, group, group * 2, group * 3):
            if idx >= len(scenes):
                continue
            start_frac = sum(sc.get("fraction", 0.0) for sc in scenes[:idx])
            title = " ".join(str(scenes[idx].get("title") or "").split())[:80]
            title = title or f"Part {len(chapters) + 1}"
            chapters.append(f"{self._format_ts(start_frac * duration)} {title}")
        return chapters
