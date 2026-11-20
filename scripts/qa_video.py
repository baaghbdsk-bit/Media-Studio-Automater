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
from typing import List, Optional

_FFMPEG_FALLBACK = r"C:\Users\gvive\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"


def _bin(name: str) -> str:
    return shutil.which(name) or (name if name != "ffmpeg" else _FFMPEG_FALLBACK)


_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg")
_VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".webm", ".mkv")


def _image_magic(head: bytes, path: Path) -> Optional[str]:
    if path.suffix.lower() == ".svg":
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:2048]
        except OSError:
            text = ""
        return None if "<svg" in text.lower() else "invalid image (svg marker missing)"
    if (head.startswith(b"\xff\xd8\xff")            # JPEG
            or head.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
            or head.startswith((b"GIF87a", b"GIF89a"))  # GIF
            or head.startswith(b"BM")                # BMP
            or (len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP")):
        return None
    return "invalid image magic bytes"


def _video_magic(head: bytes) -> Optional[str]:
    if len(head) >= 12 and head[4:8] == b"ftyp":  # MP4 / MOV / M4V
        return None
    if head.startswith(b"\x1aE\xdf\xa3"):  # WebM / Matroska
        return None
    return "invalid video magic bytes"


def _media_magic_error(path: Path, kind: str) -> Optional[str]:
    """Return a media integrity error, or None when the file looks valid."""
    try:
        with path.open("rb") as handle:
            head = handle.read(16)
    except OSError as exc:
        return f"cannot read asset: {exc}"
    lower = path.suffix.lower()
    if lower in _IMAGE_EXTS:
        return _image_magic(head, path)
    if lower in _VIDEO_EXTS:
        return _video_magic(head)
    if kind == "video":
        return _video_magic(head)
    if kind == "image":
        return _image_magic(head, path)
    return None  # Unknown type: do not reject on magic alone.


def validate_manifest(manifest_path: str, composition_dir: Optional[Path] = None) -> List[str]:
    """Validate a visual manifest; return a list of structured error strings."""
    errors: List[str] = []
    path = Path(manifest_path)
    if not path.is_file():
        return [f"manifest missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"manifest unreadable: {exc}"]
    if not isinstance(data, dict):
        return ["manifest root is not an object"]

    topic = str(data.get("topic") or "")
    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        return ["manifest.scenes is not a list"]
    base = (composition_dir or path.parent).resolve()
    sha_topics: dict = {}

    for index, scene in enumerate(scenes):
        label = "scene[%d]" % index
        if not isinstance(scene, dict):
            errors.append(f"{label}: not an object")
            continue
        # A scene may override the manifest-level topic (e.g. a merged topic).
        scene_topic = str(
            scene.get("topic") or scene.get("source_topic") or topic
        )

        # Duration must match the narration span within 0.5s.
        raw_duration = scene.get("duration_s")
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            duration = None
            errors.append(f"{label}: invalid duration_s")
        span = scene.get("narration_span")
        span_len = None
        if isinstance(span, dict):
            try:
                span_len = float(span["end_s"]) - float(span["start_s"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{label}: invalid narration_span start_s/end_s")
        else:
            errors.append(f"{label}: missing narration_span")
        if duration is not None and span_len is not None and abs(duration - span_len) > 0.5:
            errors.append(
                f"{label}: duration_s {duration:.2f} differs from narration span "
                f"{span_len:.2f}s by more than 0.5s"
            )

        if scene.get("relevance_assessed") is not True:
            errors.append(f"{label}: relevance_assessed is not true")

        asset = scene.get("asset")
        if not isinstance(asset, dict):
            errors.append(f"{label}: missing asset")
            continue
        kind = str(asset.get("type") or "").strip().lower()
        local_path = asset.get("local_path")
        markup = asset.get("inline_markup")
        is_markup = kind == "markup" or (not local_path and bool(markup))

        # Licensing is required for third-party media; own-generated markup is exempt.
        if not is_markup:
            if not str(asset.get("license") or "").strip():
                errors.append(f"{label}: asset missing license")
            if not str(asset.get("attribution") or "").strip():
                errors.append(f"{label}: asset missing attribution")
        elif not str(markup or "").strip():
            errors.append(f"{label}: markup asset has no inline_markup")

        if isinstance(local_path, str) and local_path.strip():
            resolved = Path(local_path)
            if not resolved.is_absolute():
                resolved = base / resolved
            resolved = resolved.resolve()
            try:
                resolved.relative_to(base)
            except ValueError:
                errors.append(f"{label}: asset path escapes composition dir: {local_path}")
            if not resolved.exists():
                errors.append(f"{label}: asset file missing: {local_path}")
            else:
                try:
                    size = resolved.stat().st_size
                except OSError as exc:
                    size = 0
                    errors.append(f"{label}: cannot stat asset: {exc}")
                if size <= 0:
                    errors.append(f"{label}: asset file is empty: {local_path}")
                else:
                    magic_error = _media_magic_error(resolved, kind)
                    if magic_error:
                        errors.append(f"{label}: {magic_error}: {local_path}")

        # A single asset must not be claimed by scenes about different topics.
        sha = str(asset.get("sha256") or "").strip()
        if sha:
            previous = sha_topics.get(sha)
            if previous is not None and previous != scene_topic:
                errors.append(
                    f"{label}: sha256 {sha[:12]} reused across different topics "
                    f"('{previous}' vs '{scene_topic}')"
                )
            else:
                sha_topics[sha] = scene_topic
    return errors


def check_video(path: str, manifest_path: Optional[str] = None) -> tuple[bool, dict]:
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

    if manifest_path:
        manifest_errors = validate_manifest(manifest_path, composition_dir=p.parent)
        if manifest_errors:
            report["manifest"] = {"path": str(manifest_path), "errors": manifest_errors}
            report["errors"].append(
                f"visual manifest validation failed: {len(manifest_errors)} issue(s)"
            )

    ok = not report["errors"]
    report["passed"] = ok
    return ok, report


def main() -> int:
    manifest = None
    videos: List[str] = []
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--manifest", "-m"):
            if i + 1 >= len(args):
                print("error: --manifest requires a path")
                return 2
            manifest = args[i + 1]
            i += 2
            continue
        if arg.startswith("--manifest="):
            manifest = arg.split("=", 1)[1]
            i += 1
            continue
        videos.append(arg)
        i += 1

    if not videos:
        print("usage: python scripts/qa_video.py [--manifest manifest.json] <video.mp4> [more.mp4 ...]")
        return 2
    all_ok = True
    for raw in videos:
        ok, report = check_video(raw, manifest_path=manifest)
        all_ok = all_ok and ok
        print(f"[QA] {Path(raw).name}: {'PASS' if ok else 'FAIL'}")
        for key in ("duration_s", "resolution", "fps", "frozen_total_s", "frozen_max_s",
                    "black_total_s", "loudness_lufs"):
            if key in report:
                print(f"     {key}: {report[key]}")
        for error in report["errors"]:
            print(f"     ERROR: {error}")
        manifest_report = report.get("manifest")
        if manifest_report:
            print(f"     manifest: {manifest_report['path']}")
            for error in manifest_report["errors"]:
                print(f"       MANIFEST ERROR: {error}")
        for warning in report["warnings"]:
            print(f"     WARN: {warning}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
