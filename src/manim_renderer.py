"""
Manim Community Edition Video Renderer
Primary animation engine for professional educational videos.
Supports YouTube Shorts (9:16), Instagram Reels (9:16), and YouTube Explainers (16:9).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.video_config import (
    VIDEO_FORMATS,
    get_format,
    MANIM_QUALITY,
    MANIM_FRAME_RATE,
    MANIM_RENDERER,
    BASE_DIR,
    OUTPUT_BASE,
    MIN_VIDEO_SIZE_KB,
)


class ManimRenderer:
    """
    Renders videos using Manim Community Edition as the primary animation engine.
    Generates scene-by-scene Manim Python code from script segments.
    """

    def __init__(self, output_root: Optional[Path] = None):
        self.output_root = output_root or (OUTPUT_BASE / "videos")
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.manim_available = self._check_manim()

    def _check_manim(self) -> bool:
        try:
            result = subprocess.run(
                ["manim", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def render_video(
        self,
        script_data: Dict[str, Any],
        project_dir: Path,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        fmt_key = script_data.get("format_key", "youtube_shorts")
        fmt = get_format(fmt_key)

        project_dir = Path(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        manim_code = self._generate_manim_code(script_data, fmt)

        manim_path = project_dir / "manim_source.py"
        with open(manim_path, "w", encoding="utf-8") as f:
            f.write(manim_code)

        if dry_run:
            return {
                "video_path": str(manim_path),
                "srt_path": None,
                "audio_path": None,
                "duration": script_data.get("total_duration", 0),
                "success": True,
                "dry_run": True,
                "manim_code": manim_code,
            }

        if not self.manim_available:
            return {
                "video_path": None,
                "srt_path": None,
                "audio_path": None,
                "duration": None,
                "success": False,
                "error": "Manim not installed. Install with: pip install manim",
            }

        video_path = project_dir / "final_video.mp4"
        render_result = self._run_manim_render(manim_path, project_dir, fmt)

        if not render_result["success"]:
            return render_result

        if not video_path.exists():
            manim_output = self._find_manim_output(project_dir)
            if manim_output:
                import shutil
                shutil.copy2(manim_output, video_path)

        qa_result = self._verify_video(video_path, fmt, script_data.get("total_duration", 0))

        return {
            "video_path": str(video_path) if video_path.exists() else None,
            "srt_path": str(project_dir / "subtitles.srt") if (project_dir / "subtitles.srt").exists() else None,
            "audio_path": str(project_dir / "narration.wav") if (project_dir / "narration.wav").exists() else None,
            "duration": script_data.get("total_duration", 0),
            "success": qa_result["passed"],
            "qa_checks": qa_result,
            "manim_code": manim_code,
        }

    def _generate_manim_code(
        self,
        script_data: Dict[str, Any],
        fmt: VideoFormat,
    ) -> str:
        scenes = script_data.get("body_segments", [])
        hook = script_data.get("hook", "")
        introduction = script_data.get("introduction", "")
        conclusion = script_data.get("conclusion", "")

        width, height = fmt.width, fmt.height

        code = f'''"""
Manim-generated video: {script_data.get("title", "Educational Video")}
Format: {fmt.name}
Duration: {script_data.get("total_duration", 0)} seconds
Resolution: {width}x{height} ({fmt.aspect_ratio})
FPS: {fmt.fps}
"""

from manim import *
import numpy as np

config.pixel_width = {width}
config.pixel_height = {height}
config.frame_rate = {fmt.fps}
config.background_color = "#0A0A0F"
config.quality = "{MANIM_QUALITY}"
config.frame_rate = {fmt.fps}


class EducationalVideo(Scene):
    def construct(self):
        hook_text = Text("{self._escape_text(hook)}", font_size=44, color="#00D4FF")
        hook_text.to_edge(UP, buff=1.0)
        self.play(Write(hook_text), run_time=2.0)
        self.wait(1.0)
        self.play(FadeOut(hook_text), run_time=0.5)

        intro_text = Text("{self._escape_text(introduction)}", font_size=32, color="#FFFFFF")
        intro_text.to_edge(DOWN, buff=1.0)
        self.play(FadeIn(intro_text), run_time=1.5)
        self.wait(2.0)
        self.play(FadeOut(intro_text), run_time=0.5)
'''

        for i, segment in enumerate(scenes):
            segment_title = segment.get("title", f"Segment {i+1}")
            segment_narration = segment.get("narration", "")
            segment_duration = segment.get("duration", 15.0)
            visual_desc = segment.get("visual_description", "")
            animation_type = segment.get("animation_type", "concept")

            code += f'''
        seg_title_{i} = Text("{self._escape_text(segment_title)}", font_size=40, color="#7B2CBF")
        seg_title_{i}.to_edge(UP, buff=0.5)
        self.play(Write(seg_title_{i}), run_time=1.0)

        seg_content_{i} = Text("{self._escape_text(segment_narration[:200])}...", font_size=28, color="#FFFFFF")
        seg_content_{i}.to_edge(DOWN, buff=1.0)
        self.play(FadeIn(seg_content_{i}), run_time=1.0)

        visual_{i} = self._create_visual("{animation_type}", "{self._escape_text(visual_desc)}")
        self.play(Create(visual_{i}), run_time=2.0)
        self.wait({max(segment_duration - 5.0, 2.0)})
        self.play(FadeOut(seg_title_{i}), FadeOut(seg_content_{i}), FadeOut(visual_{i}), run_time=0.5)

        conclusion_text = Text("{self._escape_text(conclusion)}", font_size=36, color="#00D4FF")
        conclusion_text.move_to(ORIGIN)
        self.play(Write(conclusion_text), run_time=2.0)
        self.wait(3.0)
        self.play(FadeOut(conclusion_text), run_time=0.5)

    def _create_visual(self, animation_type: str, description: str):
        if animation_type == "concept":
            card = RoundedRectangle(corner_radius=0.2, width=6, height=3, color="#00D4FF")
            card.set_fill("#1A1A2E", opacity=0.9)
            text = Text(description[:50], font_size=24, color="#FFFFFF")
            text.move_to(card.get_center())
            return VGroup(card, text)
        elif animation_type == "flow":
            nodes = VGroup()
            for i in range(3):
                node = Circle(radius=0.7, color="#7B2CBF")
                node.set_fill("#1A1A2E", opacity=0.9)
                node.shift(RIGHT * (i - 1) * 2.5)
                label = Text(f"Step {{i+1}}", font_size=20, color="#FFFFFF")
                label.move_to(node.get_center())
                nodes.add(VGroup(node, label))
            arrows = VGroup()
            for i in range(2):
                arrow = Arrow(
                    nodes[i][0].get_right(),
                    nodes[i+1][0].get_left(),
                    color="#00D4FF",
                )
                arrows.add(arrow)
            return VGroup(nodes, arrows)
        elif animation_type == "analogy":
            cards = VGroup()
            for i in range(2):
                card = RoundedRectangle(corner_radius=0.2, width=4, height=2.5, color="#FF6B35")
                card.set_fill("#1A1A2E", opacity=0.9)
                card.shift(DOWN * 0.5 + RIGHT * (i - 0.5) * 4.5)
                text = Text(description[:40], font_size=20, color="#FFFFFF")
                text.move_to(card.get_center())
                cards.add(VGroup(card, text))
            return cards
        elif animation_type == "takeaway":
            highlight = Rectangle(width=7, height=2, color="#00D4FF")
            highlight.set_fill("#00D4FF", opacity=0.1)
            text = Text(description[:60], font_size=30, color="#00D4FF", weight=BOLD)
            text.move_to(highlight.get_center())
            return VGroup(highlight, text)
        elif animation_type == "code":
            code_block = Code(
                code=description[:100],
                tab_width=4,
                background="window",
                language="python",
                font_size=20,
            )
            return code_block
        elif animation_type == "chart":
            chart = VGroup()
            for i, val in enumerate([3, 5, 4, 7, 6]):
                bar = Rectangle(width=0.6, height=val, color="#7B2CBF")
                bar.set_fill("#7B2CBF", opacity=0.8)
                bar.shift(RIGHT * (i - 2) * 1.2 + DOWN * 2)
                chart.add(bar)
            return chart
        else:
            card = RoundedRectangle(corner_radius=0.2, width=6, height=3, color="#FFFFFF")
            card.set_fill("#1A1A2E", opacity=0.9)
            text = Text(description[:50], font_size=24, color="#FFFFFF")
            text.move_to(card.get_center())
            return VGroup(card, text)

    def _escape_text(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def _run_manim_render(
        self,
        manim_path: Path,
        output_dir: Path,
        fmt: VideoFormat,
    ) -> Dict[str, Any]:
        manim_media_dir = output_dir / "manim_media"
        manim_media_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "manim",
            str(manim_path),
            "EducationalVideo",
            "-q", MANIM_QUALITY,
            "-r", f"{fmt.width},{fmt.height}",
            "--fps", str(fmt.fps),
            "--media_dir", str(manim_media_dir),
            "--output_name", "final_video",
        ]

        if MANIM_RENDERER == "opengl":
            cmd.extend(["-r", "opengl"])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(output_dir),
            )

            if proc.returncode != 0:
                return {
                    "success": False,
                    "error": f"Manim render failed: {proc.stderr[-1000:]}",
                }

            return {"success": True, "media_dir": str(manim_media_dir)}

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Manim render timed out (10 minutes)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _find_manim_output(self, project_dir: Path) -> Optional[Path]:
        for pattern in ["**/*.mp4", "**/final_video*"]:
            for f in project_dir.glob(pattern):
                if f.suffix == ".mp4":
                    return f
        return None

    def _verify_video(
        self,
        video_path: Path,
        fmt: VideoFormat,
        expected_duration: float,
    ) -> Dict[str, Any]:
        checks = {
            "resolution": False,
            "aspect_ratio": False,
            "fps": False,
            "duration": False,
            "file_exists": False,
            "file_size": False,
            "audio_present": False,
            "passed": False,
        }

        if not video_path.exists():
            checks["passed"] = False
            return checks

        checks["file_exists"] = True
        checks["file_size"] = video_path.stat().st_size > MIN_VIDEO_SIZE_KB * 1024

        try:
            proc = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,r_frame_rate,duration",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            data = json.loads(proc.stdout)

            streams = data.get("streams", [])
            if streams:
                stream = streams[0]
                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
                fps_str = stream.get("r_frame_rate", "0/1")
                fps = eval(fps_str) if "/" in fps_str else float(fps_str)

                checks["resolution"] = (width == fmt.width and height == fmt.height)
                checks["aspect_ratio"] = abs((width / height) - (fmt.width / fmt.height)) < 0.01
                checks["fps"] = abs(fps - fmt.fps) < 1.0

            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0))
            checks["duration"] = abs(duration - expected_duration) < expected_duration * 0.2

            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
            checks["audio_present"] = len(audio_streams) > 0

        except Exception:
            pass

        checks["passed"] = (
            checks["file_exists"]
            and checks["file_size"]
            and checks["resolution"]
            and checks["duration"]
        )

        return checks