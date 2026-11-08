"""
3D Animated Educational Presenter Engine ("Nova").
Produces vertical 1080x1920 (9:16) educational Shorts and Reels with:
- Consistent 3D humanoid presenter character ("Nova")
- Natural skeletal movement, continuous breathing sway, and dynamic blinking
- Speech-synchronized lip-sync (viseme-driven jaw/mouth opening)
- Natural character gestures (pointing, welcoming, explaining, hero takeaway)
- Interactive 3D visual demonstrations (Merkle trees, neural networks, chip architecture)
- Multi-shot cinematic camera system (Medium Push-in, Split Demo, Dynamic Close-up, Hero Wide)
- High-contrast broadcast graphics and live HUD metrics
"""
import re
from pathlib import Path
from typing import Dict, Any, Optional

from .storyboard_ai import StoryboardAI
from .audio_lipsync import AudioLipSyncEngine
from .presenter_renderer import PresenterRenderer


class Presenter3DStudio:
    def __init__(self, output_root: Optional[Path] = None, fps: int = 24):
        self.output_root = Path(output_root) if output_root else Path("generated_visuals/videos")
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.storyboard_ai = StoryboardAI()
        self.renderer = PresenterRenderer(fps=self.fps)

    def generate_presenter_video(
        self,
        topic_data: Dict[str, Any],
        custom_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        End-to-end autonomous pipeline:
        1. AI Storyboard & Script generation with topic-aware 3D demo selection
        2. Neural speech synthesis & frame-accurate viseme extraction
        3. Headless WebGL frame-by-frame 3D rendering & FFmpeg encoding
        4. Production packaging (MP4, SRT, Audio, Metadata)
        """
        title = topic_data.get("title", "Technical Breakdown")
        slug = custom_slug or re.sub(r"[^\w\-]", "_", title.lower())[:35]
        work_dir = self.output_root / f"presenter_3d_{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=======================================================", flush=True)
        print(f"[Presenter3DStudio] Generating: '{title}'", flush=True)
        print(f"[Presenter3DStudio] Output Directory: {work_dir}", flush=True)
        print(f"=======================================================", flush=True)

        # 1. Plan Storyboard & Visual Demo
        print(f"[Presenter3DStudio] Planning 3D storyboard & script...", flush=True)
        storyboard = self.storyboard_ai.plan_3d_presentation(topic_data)
        script_text = storyboard.get("narration", "")

        # 2. Synthesize Speech & Compute Visemes
        audio_engine = AudioLipSyncEngine(output_dir=work_dir, fps=self.fps)
        audio_result = audio_engine.generate_narration_and_visemes(script_text, filename_prefix="narration")
        audio_path = Path(audio_result["audio_path"])
        visemes = audio_result["visemes"]

        # 3. Render 3D Video via Headless Playwright & FFmpeg
        final_mp4 = work_dir / f"presenter_3d_{slug}.mp4"
        render_result = self.renderer.render(
            storyboard=storyboard,
            visemes=visemes,
            audio_path=audio_path,
            output_path=final_mp4,
            work_dir=work_dir
        )

        # 4. Assemble Full Production Package
        result = {
            "title": title,
            "category": storyboard.get("category", "SYSTEMS"),
            "video_path": str(final_mp4),
            "srt_path": render_result.get("srt_path"),
            "audio_path": str(audio_path),
            "duration": render_result.get("duration"),
            "fps": self.fps,
            "frames": render_result.get("frames"),
            "file_size_mb": render_result.get("file_size_mb"),
            "storyboard": storyboard,
            "format": "1080x1920 (9:16 Vertical Short)",
            "presenter": "Nova (3D Humanoid)",
            "visual_demo": storyboard.get("demo_type")
        }

        print(f"[Presenter3DStudio] SUCCESS! 3D Presenter Video Generation COMPLETE!", flush=True)
        print(f"   Video File: {final_mp4} ({result['file_size_mb']} MB, {result['duration']:.1f}s)", flush=True)
        print(f"   Subtitles:  {result['srt_path']}", flush=True)
        return result
