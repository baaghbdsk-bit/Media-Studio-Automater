"""
Subtitle Generator
Generates synchronized SRT and ASS subtitle files from narration segments.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.video_config import SUBTITLE_OUTPUT_DIR


class SubtitleGenerator:
    """
    Generates synchronized subtitles in SRT and ASS formats.
    Supports word-level and phrase-level synchronization.
    """

    def __init__(self, output_root: Optional[Path] = None):
        self.output_root = output_root or SUBTITLE_OUTPUT_DIR
        self.output_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_ass_timestamp(seconds: float) -> str:
        """Format seconds to ASS timestamp (H:MM:SS.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def generate_srt(
        self,
        segments: List[dict],
        output_name: str = "subtitles",
    ) -> Path:
        """
        Generate SRT subtitle file from timed segments.

        Args:
            segments: List of dicts with 'start', 'end', 'text' keys
            output_name: Output filename without extension

        Returns:
            Path to generated SRT file
        """
        output_path = self.output_root / f"{output_name}.srt"

        srt_blocks = []
        for i, seg in enumerate(segments, 1):
            start = self._format_timestamp(seg["start"])
            end = self._format_timestamp(seg["end"])
            text = seg["text"].strip()
            srt_blocks.append(f"{i}\n{start} --> {end}\n{text}\n")

        output_path.write_text("\n".join(srt_blocks), encoding="utf-8")
        return output_path

    def generate_ass(
        self,
        segments: List[dict],
        output_name: str = "subtitles",
        style_name: str = "Default",
    ) -> Path:
        """
        Generate ASS subtitle file with styling.

        Args:
            segments: List of dicts with 'start', 'end', 'text' keys
            output_name: Output filename without extension
            style_name: ASS style name

        Returns:
            Path to generated ASS file
        """
        output_path = self.output_root / f"{output_name}.ass"

        # ASS header
        header = """[Script Info]
Title: Media Studio Automater Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,1,2,30,30,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        for i, seg in enumerate(segments):
            start = self._format_ass_timestamp(seg["start"])
            end = self._format_ass_timestamp(seg["end"])
            text = seg["text"].strip()
            events.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}")

        output_path.write_text(header + "\n".join(events), encoding="utf-8")
        return output_path

    def generate_from_script(
        self,
        script_data: Dict[str, Any],
        output_name: Optional[str] = None,
    ) -> Dict[str, Path]:
        """
        Generate both SRT and ASS subtitles from a VideoScript dict.

        Args:
            script_data: VideoScript as dict
            output_name: Optional output filename

        Returns:
            Dict with 'srt' and 'ass' paths
        """
        if not output_name:
            output_name = script_data.get("script_id", "subtitles")

        # Build segments from script
        segments = []
        current_time = 0.0
        for seg in script_data.get("body_segments", []):
            segments.append({
                "start": current_time,
                "end": current_time + seg.get("duration", 15.0),
                "text": seg.get("narration", ""),
            })
            current_time += seg.get("duration", 15.0)

        # Add hook and conclusion as separate segments
        if script_data.get("hook"):
            segments.insert(0, {
                "start": 0.0,
                "end": 3.0,
                "text": script_data["hook"],
            })
        if script_data.get("conclusion"):
            segments.append({
                "start": current_time,
                "end": current_time + 5.0,
                "text": script_data["conclusion"],
            })

        srt_path = self.generate_srt(segments, output_name)
        ass_path = self.generate_ass(segments, output_name)

        return {"srt": srt_path, "ass": ass_path}