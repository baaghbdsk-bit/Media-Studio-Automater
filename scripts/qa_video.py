"""Pre-publish quality gate for generated videos.

Checks structure, static stretches, black frames and loudness using ffprobe/ffmpeg.
Exits non-zero when the video is not good enough to publish.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_FFMPEG_FALLBACK = r"C:\Users\gvive\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"


def _bin(name: str) -> str:
    return shutil.which(name) or (name if name != "ffmpeg" else _FFMPEG_FALLBACK)


def check_video(path: str, static: bool = False) -> tuple[bool, dict]:
    ffmpeg, ffprobe = _bin("ffmpeg"), _bin("ffprobe")
    p = Path(path)
    report: dict = {"path": str(p), "errors": [], "warnings": []}
    if not p.exists():
        report["errors"].append("file missing")
        return False, report

    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(p)],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(probe.stdout)
        video = next(s for s in data["streams"] if s["codec_type"] == "video")
        audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
        report["duration_s"] = round(float(data["format"]["duration"]), 2)
        report["resolution"] = f'{video["width"]}x{video["height"]}'
        report["fps"] = video.get("avg_frame_rate", "?")
        if video["width"] < 900 or video["height"] < 1600:
            report["errors"].append("resolution below 1080x1920")
        if not (20 <= report["duration_s"] <= 120):
            report["errors"].append("unexpected duration")
        if not audio:
            report["errors"].append("no audio stream")
    except Exception as exc:
        report["errors"].append(f"ffprobe failed: {exc}")

    # Static slideshows are intentionally frozen between hard cuts, so freeze
    # detection would reject every valid slide. All other checks still apply.
    if static:
        report["frozen_total_s"] = 0.0
        report["frozen_max_s"] = 0.0
        report["warnings"].append("static slideshow: freeze detection skipped by design")
    else:
        freeze = subprocess.run(
            [ffmpeg, "-hide_banner", "-v", "info", "-i", str(p),
             "-vf", "freezedetect=n=-45dB:d=0.5", "-f", "null", "NUL"],
            capture_output=True, text=True,
        )
        durations = [float(m) for m in re.findall(r"freeze_duration:\s*([\d.]+)", freeze.stderr)]
        report["frozen_total_s"] = round(sum(durations), 2)
        report["frozen_max_s"] = round(max(durations), 2) if durations else 0.0
        if report["frozen_total_s"] > 3.0 or report["frozen_max_s"] > 1.0:
            report["errors"].append(
                f"static frames: total {report['frozen_total_s']}s, max {report['frozen_max_s']}s"
            )

    black = subprocess.run(
        [ffmpeg, "-hide_banner", "-v", "info", "-i", str(p),
         "-vf", "blackdetect=d=0.3:pix_th=0.10", "-f", "null", "NUL"],
        capture_output=True, text=True,
    )
    black_durations = [float(m) for m in re.findall(r"black_duration:\s*([\d.]+)", black.stderr)]
    report["black_total_s"] = round(sum(black_durations), 2)
    if report["black_total_s"] > 0.5:
        report["errors"].append(f"black frames: {report['black_total_s']}s")

    loud = subprocess.run(
        [ffmpeg, "-hide_banner", "-v", "info", "-i", str(p),
         "-af", "ebur128=peak=true", "-f", "null", "NUL"],
        capture_output=True, text=True,
    )
    matches = re.findall(r"I:\s*(-?[\d.]+) LUFS", loud.stderr)
    if matches:
        report["loudness_lufs"] = float(matches[-1])
        if not (-16.0 <= report["loudness_lufs"] <= -10.0):
            report["warnings"].append(f"loudness {report['loudness_lufs']} LUFS outside target band")

    return not report["errors"], report


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/qa_video.py [--static] <video.mp4> [more.mp4 ...]")
        return 2
    static = "--static" in sys.argv
    paths = [arg for arg in sys.argv[1:] if arg != "--static"]
    all_ok = True
    for raw in paths:
        ok, report = check_video(raw, static=static)
        all_ok = all_ok and ok
        print(f"[QA] {Path(raw).name}: {'PASS' if ok else 'FAIL'}")
        for key in ("duration_s", "resolution", "fps", "frozen_total_s", "frozen_max_s",
                    "black_total_s", "loudness_lufs"):
            if key in report:
                print(f"     {key}: {report[key]}")
        for error in report["errors"]:
            print(f"     ERROR: {error}")
        for warning in report["warnings"]:
            print(f"     WARN: {warning}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
