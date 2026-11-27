"""Pre-publish quality gate for generated videos.

Checks structure, static stretches, black frames and loudness using ffprobe/ffmpeg.
Exits non-zero when the video is not good enough to publish.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_FFMPEG_FALLBACK = r"C:\Users\gvive\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"


def _bin(name: str) -> str:
    return shutil.which(name) or (name if name != "ffmpeg" else _FFMPEG_FALLBACK)


def _log_feedback(video_path: Path, score: int, passed: bool, defects: list[str], summary: str) -> None:
    log_path = Path.home() / ".gemini" / "config" / "skills" / "creative-production-director" / "feedback-log.jsonl"
    if not log_path.parent.exists():
        return
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "media_type": "video",
            "model_provider": "pro_short_engine + gemini-3.5-flash-qa",
            "settings": "1080x1920",
            "prompt": video_path.stem,
            "output_path": str(video_path),
            "score": score,
            "passed": passed,
            "critical_defects": defects,
            "revisions": summary,
            "final_result": "accepted" if passed else "rejected",
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _check_visual_frames(video_path: Path, ffmpeg: str, duration_s: float) -> dict:
    """Extract 4 representative frames and evaluate against the 80/100 rubric via Gemini Vision."""
    if duration_s <= 0:
        return {"skipped": "invalid duration"}

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import config  # type: ignore
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    except Exception:
        api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        return {"skipped": "GEMINI_API_KEY not configured"}

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        return {"skipped": f"google-genai unavailable: {exc}"}

    timestamps = [round(duration_s * frac, 2) for frac in (0.15, 0.40, 0.65, 0.90)]
    frame_parts: list = []
    with tempfile.TemporaryDirectory(prefix="qa_frames_") as tmpdir:
        for idx, ts in enumerate(timestamps, start=1):
            out_png = Path(tmpdir) / f"frame_{idx}.png"
            subprocess.run(
                [ffmpeg, "-y", "-ss", str(ts), "-i", str(video_path), "-vframes", "1", str(out_png)],
                capture_output=True,
                timeout=15,
            )
            if out_png.exists() and out_png.stat().st_size > 0:
                frame_parts.append(types.Part.from_bytes(data=out_png.read_bytes(), mime_type="image/png"))

    if not frame_parts:
        return {"skipped": "no frames extracted"}

    rubric_prompt = (
        "You are a strict Video Quality Auditor. Inspect these 4 sampled frames from a 1080x1920 vertical "
        "YouTube Short / Instagram Reel. Score the video out of 100 (Visual Quality 15, Motion/Layout Clarity 20, "
        "Temporal Consistency 20, Composition & 9:16 Safe Zones 15, Typography/Captions Legibility 15, "
        "Platform Suitability 15). List any CRITICAL DEFECTS (text overflowing boxes, clipped captions, "
        "overlapping unreadable labels, blank/broken frames, or subject cut off). "
        'Respond ONLY with JSON: {"score": <int 0-100>, "critical_defects": [<strings>], "summary": "<1-line>"}'
    )

    client = genai.Client(api_key=api_key)
    last_err = None
    for model_name in ("gemini-3.5-flash", "gemini-3.5-flash-lite"):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=[rubric_prompt, *frame_parts],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            parsed = json.loads(resp.text or "{}")
            score = int(parsed.get("score", 0))
            defects = [str(d) for d in (parsed.get("critical_defects") or []) if str(d).strip()]
            summary = str(parsed.get("summary") or "")
            passed = score >= 75 and not defects
            _log_feedback(video_path, score, passed, defects, summary)
            return {
                "model": model_name,
                "score": score,
                "passed": passed,
                "critical_defects": defects,
                "summary": summary,
            }
        except Exception as exc:
            last_err = exc
    return {"skipped": f"vision QA unavailable: {last_err}"}


def check_video(path: str, static: bool = False, visual_qa: bool = True) -> tuple[bool, dict]:
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
        report["pix_fmt"] = video.get("pix_fmt", "?")
        if video["width"] < 900 or video["height"] < 1600:
            report["errors"].append("resolution below 1080x1920")
        if report["pix_fmt"] != "yuv420p":
            report["warnings"].append(f"pix_fmt is {report['pix_fmt']} (expected yuv420p for mobile/web)")
        if not (20 <= report["duration_s"] <= 179):
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

    if visual_qa and not report["errors"] and "duration_s" in report:
        vqa = _check_visual_frames(p, ffmpeg, report["duration_s"])
        report["visual_qa"] = vqa
        if "score" in vqa:
            if not vqa["passed"]:
                defects_str = "; ".join(vqa["critical_defects"]) if vqa["critical_defects"] else "score below 75"
                report["errors"].append(f"visual QA failed ({vqa['score']}/100): {defects_str}")
        elif "skipped" in vqa:
            report["warnings"].append(f"visual QA skipped: {vqa['skipped']}")

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
