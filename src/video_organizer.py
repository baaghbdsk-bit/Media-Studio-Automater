"""
Video Organizer
Organizes output files into per-project folders with all supporting assets.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.video_config import (
    PROJECTS_DIR,
    VIDEO_OUTPUT_DIR,
    SCRIPT_OUTPUT_DIR,
    SUBTITLE_OUTPUT_DIR,
    AUDIO_OUTPUT_DIR,
    THUMBNAIL_OUTPUT_DIR,
    BASE_DIR,
    get_format,
)


class VideoOrganizer:
    def __init__(self, projects_dir: Optional[Path] = None):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        project_id: str,
        script_data: Dict[str, Any],
        video_data: Dict[str, Any],
        audio_data: Optional[Dict[str, Any]] = None,
        subtitle_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        project_dir = self.projects_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "assets").mkdir(exist_ok=True)

        if video_data.get("video_path"):
            src = Path(video_data["video_path"])
            if src.exists():
                shutil.copy2(src, project_dir / "final_video.mp4")

        self._save_script_markdown(script_data, project_dir / "script.md")

        scene_plan = {
            "script_id": script_data.get("script_id"),
            "format_key": script_data.get("format_key"),
            "total_duration": script_data.get("total_duration"),
            "segments": [
                {
                    "title": seg.get("title"),
                    "duration": seg.get("duration"),
                    "start_time": seg.get("start_time"),
                    "end_time": seg.get("end_time"),
                    "visual_description": seg.get("visual_description"),
                    "animation_type": seg.get("animation_type"),
                }
                for seg in script_data.get("body_segments", [])
            ],
        }
        with open(project_dir / "scene_plan.json", "w", encoding="utf-8") as f:
            json.dump(scene_plan, f, indent=2, ensure_ascii=False)

        if audio_data:
            with open(project_dir / "audio_info.json", "w", encoding="utf-8") as f:
                json.dump(audio_data, f, indent=2, ensure_ascii=False)
            if audio_data.get("audio_path"):
                src = Path(audio_data["audio_path"])
                if src.exists():
                    shutil.copy2(src, project_dir / "narration.wav")

        if subtitle_data:
            if subtitle_data.get("srt"):
                src = Path(subtitle_data["srt"])
                if src.exists():
                    shutil.copy2(src, project_dir / "subtitles.srt")
            if subtitle_data.get("ass"):
                src = Path(subtitle_data["ass"])
                if src.exists():
                    shutil.copy2(src, project_dir / "subtitles.ass")

        if video_data.get("manim_code"):
            with open(project_dir / "manim_source.py", "w", encoding="utf-8") as f:
                f.write(video_data["manim_code"])

        project_metadata = {
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "script_id": script_data.get("script_id"),
            "format_key": script_data.get("format_key"),
            "total_duration": script_data.get("total_duration"),
            "title": script_data.get("title"),
            "topic": script_data.get("topic"),
            "video": video_data,
            "audio": audio_data,
            "subtitles": subtitle_data,
            "platform_metadata": metadata or {},
        }
        with open(project_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(project_metadata, f, indent=2, ensure_ascii=False)

        if script_data.get("source_topic"):
            with open(project_dir / "sources.md", "w", encoding="utf-8") as f:
                f.write("# Sources\n\n")
                topic = script_data["source_topic"]
                f.write(f"- Title: {topic.get('title', 'N/A')}\n")
                f.write(f"- Summary: {topic.get('summary', 'N/A')}\n")
                f.write(f"- Category: {topic.get('category', 'N/A')}\n")

        self._generate_thumbnail_placeholder(project_dir, script_data)

        return project_dir

    def _save_script_markdown(
        self,
        script_data: Dict[str, Any],
        output_path: Path,
    ) -> None:
        lines = []
        lines.append(f"# {script_data.get('title', 'Untitled')}\n")
        lines.append(f"**Format:** {script_data.get('format_key', 'N/A')}")
        lines.append(f"**Duration:** {script_data.get('total_duration', 0):.1f} seconds")
        lines.append(f"**Created:** {script_data.get('created_at', 'N/A')}\n")
        lines.append(f"## Hook\n\n{script_data.get('hook', '')}\n")
        lines.append(f"## Introduction\n\n{script_data.get('introduction', '')}\n")
        lines.append(f"## Segments\n")
        for seg in script_data.get("body_segments", []):
            lines.append(f"\n### {seg.get('title', 'Segment')} ({seg.get('duration', 0):.1f}s)")
            lines.append(f"\n{seg.get('narration', '')}")
            lines.append(f"\n*Visual:* {seg.get('visual_description', '')}")
            lines.append(f"\n*Animation:* {seg.get('animation_type', 'concept')}")
        lines.append(f"\n## Conclusion\n\n{script_data.get('conclusion', '')}\n")
        if script_data.get("call_to_action"):
            lines.append(f"## Call to Action\n\n{script_data['call_to_action']}\n")
        lines.append(f"\n## Full Narration\n\n{script_data.get('narration_full', '')}\n")

        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _generate_thumbnail_placeholder(
        self,
        project_dir: Path,
        script_data: Dict[str, Any],
    ) -> None:
        format_key = script_data.get("format_key", "youtube_shorts")
        fmt = get_format(format_key)

        thumbnail_path = project_dir / "thumbnail.png"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0A0A0F:s={fmt.width}x{fmt.height}:d=1",
            "-vf",
            f"drawtext=text='{script_data.get('title', 'Video')[:50]}':"
            f"fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2",
            "-frames:v", "1",
            str(thumbnail_path),
        ]

        try:
            import subprocess
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception:
            pass

    def list_projects(self) -> List[Dict[str, Any]]:
        projects = []
        for proj_dir in sorted(self.projects_dir.iterdir(), reverse=True):
            if proj_dir.is_dir():
                meta_path = proj_dir / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        meta["project_dir"] = str(proj_dir)
                        projects.append(meta)
                    except Exception:
                        pass
        return projects

    def get_project(self, project_id: str) -> Optional[Path]:
        project_dir = self.projects_dir / project_id
        if project_dir.exists() and project_dir.is_dir():
            return project_dir
        return None