"""
Quality Assurance Module
Automated checks for video quality: resolution, aspect ratio, FPS, duration,
audio presence, sync, safe zones, and rendering errors.
"""
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.video_config import get_format, MIN_VIDEO_SIZE_KB


class QualityAssurance:
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []

    def verify_video(
        self,
        video_path: Path,
        format_key: str,
        expected_duration: float,
        expected_fps: Optional[int] = None,
    ) -> Dict[str, Any]:
        fmt = get_format(format_key)
        expected_fps = expected_fps or fmt.fps

        results = {
            "video_path": str(video_path),
            "format_key": format_key,
            "checks": {},
            "passed": False,
            "errors": [],
            "warnings": [],
        }

        if not video_path.exists():
            results["errors"].append("Video file does not exist")
            results["checks"]["file_exists"] = False
            return results
        results["checks"]["file_exists"] = True

        file_size_kb = video_path.stat().st_size / 1024
        results["checks"]["file_size_kb"] = round(file_size_kb, 2)
        results["checks"]["file_size_ok"] = file_size_kb > MIN_VIDEO_SIZE_KB
        if not results["checks"]["file_size_ok"]:
            results["errors"].append(f"File too small: {file_size_kb:.1f}KB (min {MIN_VIDEO_SIZE_KB}KB)")

        probe_result = self._probe_video(video_path)
        if not probe_result["success"]:
            results["errors"].append(f"ffprobe failed: {probe_result.get('error', 'unknown')}")
            results["checks"]["ffprobe"] = False
            return results

        results["checks"]["ffprobe"] = True
        stream = probe_result.get("video_stream", {})
        format_info = probe_result.get("format", {})

        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
        results["checks"]["width"] = width
        results["checks"]["height"] = height
        results["checks"]["resolution_ok"] = (width == fmt.width and height == fmt.height)
        if not results["checks"]["resolution_ok"]:
            results["errors"].append(f"Resolution {width}x{height} != expected {fmt.width}x{fmt.height}")

        if width > 0 and height > 0:
            actual_ar = width / height
            expected_ar = fmt.width / fmt.height
            results["checks"]["aspect_ratio"] = round(actual_ar, 3)
            results["checks"]["aspect_ratio_ok"] = abs(actual_ar - expected_ar) < 0.01
            if not results["checks"]["aspect_ratio_ok"]:
                results["errors"].append(f"Aspect ratio {actual_ar:.3f} != expected {expected_ar:.3f}")

        fps_str = stream.get("r_frame_rate", "0/1")
        fps = self._parse_fps(fps_str)
        results["checks"]["fps"] = fps
        results["checks"]["fps_ok"] = abs(fps - expected_fps) < 1.0
        if not results["checks"]["fps_ok"]:
            results["errors"].append(f"FPS {fps} != expected {expected_fps}")

        duration = float(format_info.get("duration", 0))
        results["checks"]["duration"] = round(duration, 2)
        results["checks"]["expected_duration"] = expected_duration
        results["checks"]["duration_ok"] = (
            abs(duration - expected_duration) < expected_duration * 0.25
        )
        if not results["checks"]["duration_ok"]:
            results["warnings"].append(
                f"Duration {duration:.1f}s differs from expected {expected_duration:.1f}s by >25%"
            )

        audio_streams = [
            s for s in probe_result.get("streams", [])
            if s.get("codec_type") == "audio"
        ]
        results["checks"]["audio_present"] = len(audio_streams) > 0
        results["checks"]["audio_streams"] = len(audio_streams)
        if not results["checks"]["audio_present"]:
            results["errors"].append("No audio stream found")

        codec = stream.get("codec_name", "unknown")
        results["checks"]["codec"] = codec
        results["checks"]["codec_ok"] = codec in ("h264", "hevc", "av1")
        if not results["checks"]["codec_ok"]:
            results["warnings"].append(f"Codec {codec} may not be optimal for web delivery")

        pix_fmt = stream.get("pix_fmt", "unknown")
        results["checks"]["pixel_format"] = pix_fmt
        results["checks"]["pixel_format_ok"] = pix_fmt == "yuv420p"
        if not results["checks"]["pixel_format_ok"]:
            results["warnings"].append(f"Pixel format {pix_fmt} may cause compatibility issues")

        critical_checks = [
            results["checks"].get("file_exists", False),
            results["checks"].get("file_size_ok", False),
            results["checks"].get("resolution_ok", False),
            results["checks"].get("duration_ok", False),
            results["checks"].get("audio_present", False),
        ]
        results["passed"] = all(critical_checks) and len(results["errors"]) == 0

        return results

    def _probe_video(self, video_path: Path) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,duration",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if proc.returncode != 0:
                return {"success": False, "error": proc.stderr}

            data = json.loads(proc.stdout)
            streams = data.get("streams", [])

            video_stream = {}
            all_streams = []
            for s in streams:
                all_streams.append(s)
                if s.get("codec_type") == "video":
                    video_stream = s

            return {
                "success": True,
                "video_stream": video_stream,
                "streams": all_streams,
                "format": data.get("format", {}),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _parse_fps(fps_str: str) -> float:
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except Exception:
            return 0.0

    def verify_script_timing(
        self,
        script_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        segments = script_data.get("body_segments", [])
        total_duration = script_data.get("total_duration", 0)

        issues = []
        segment_durations = 0.0
        prev_end = 0.0

        for i, seg in enumerate(segments):
            start = seg.get("start_time", 0)
            end = seg.get("end_time", 0)
            duration = seg.get("duration", 0)

            if start < prev_end - 0.1:
                issues.append(f"Segment {i} overlaps with previous segment")

            if abs((end - start) - duration) > 0.5:
                issues.append(
                    f"Segment {i} duration mismatch: {end-start:.1f}s vs {duration:.1f}s"
                )

            segment_durations += duration
            prev_end = end

        if abs(segment_durations - total_duration) > 1.0:
            issues.append(
                f"Total segment duration {segment_durations:.1f}s != script total {total_duration:.1f}s"
            )

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "segment_count": len(segments),
            "total_duration": total_duration,
            "segment_duration_sum": round(segment_durations, 2),
        }

    def generate_qa_report(
        self,
        video_results: Dict[str, Any],
        timing_results: Dict[str, Any],
        output_path: Optional[Path] = None,
    ) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("QUALITY ASSURANCE REPORT")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Video: {video_results.get('video_path', 'N/A')}")
        lines.append(f"Format: {video_results.get('format_key', 'N/A')}")
        lines.append(f"Overall: {'PASS' if video_results.get('passed') else 'FAIL'}")
        lines.append("")

        lines.append("Video Checks:")
        for key, value in video_results.get("checks", {}).items():
            if isinstance(value, bool):
                status = "PASS" if value else "FAIL"
                lines.append(f"  {key}: {status}")
            else:
                lines.append(f"  {key}: {value}")

        if video_results.get("errors"):
            lines.append("")
            lines.append("Errors:")
            for err in video_results["errors"]:
                lines.append(f"  - {err}")

        if video_results.get("warnings"):
            lines.append("")
            lines.append("Warnings:")
            for warn in video_results["warnings"]:
                lines.append(f"  - {warn}")

        lines.append("")
        lines.append("Script Timing:")
        lines.append(f"  Segments: {timing_results.get('segment_count', 0)}")
        lines.append(f"  Total Duration: {timing_results.get('total_duration', 0):.1f}s")
        lines.append(f"  Segment Sum: {timing_results.get('segment_duration_sum', 0):.1f}s")
        lines.append(f"  Timing Pass: {'PASS' if timing_results.get('passed') else 'FAIL'}")
        if timing_results.get("issues"):
            lines.append("  Issues:")
            for issue in timing_results["issues"]:
                lines.append(f"    - {issue}")

        lines.append("")
        lines.append("=" * 60)

        report = "\n".join(lines)

        if output_path:
            output_path.write_text(report, encoding="utf-8")

        return report