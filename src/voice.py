"""
Voice narration helpers backed by Edge TTS.

This module provides:
  * ``capture_words`` - synthesize speech to an MP3 while collecting exact
    word-level timing metadata (Edge TTS ``WordBoundary`` events).
  * ``make_audition`` - render the same sample with several candidate voices
    and write a JSON manifest so a human can pick the best one.
  * ``write_srt`` - turn word timings into a standard SRT subtitle file.

Only the standard library and ``edge_tts`` are used: no ffmpeg, no numpy.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts

# Candidate voices for the audition helper.  Keys are short, file-safe labels;
# each value carries the actual Edge TTS voice name plus the prosody used when
# auditioning it.
VOICES: Dict[str, Dict[str, Any]] = {
    "Christopher": {
        "name": "en-US-ChristopherNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "Warm, conversational male narration; reliable all-rounder.",
    },
    "Ava": {
        "name": "en-US-AvaNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "Clear, friendly female narration with a natural cadence.",
    },
    "Jenny": {
        "name": "en-US-JennyNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "Bright, expressive female voice; good for explainers.",
    },
    "Guy": {
        "name": "en-US-GuyNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "Neutral, authoritative male voice; good for tutorials.",
    },
    "Aria": {
        "name": "en-US-AriaNeural",
        "rate": "-5%",
        "pitch": "+0Hz",
        "description": "Smooth, slightly slower female voice; good for storytelling.",
    },
    "Sonia": {
        "name": "en-US-SoniaNeural",
        "rate": "+0%",
        "pitch": "-2Hz",
        "description": "Calm, composed female voice with a lower register.",
    },
}

# 100 nanoseconds == 1 tick in Edge TTS WordBoundary events.
_TICKS_PER_SECOND = 10_000_000

# A cue is also closed when a word ends with one of these characters.
_CUE_END_PUNCTUATION = ".!?,;:"


async def _stream_speech(
    text: str,
    out_mp3: str,
    voice: str,
    rate: str,
    pitch: str,
    proxy: Optional[str],
) -> List[Dict[str, Any]]:
    """Stream Edge TTS audio to ``out_mp3`` and return WordBoundary words.

    Args:
        text: Text to synthesize.
        out_mp3: Destination MP3 path.
        voice: Edge TTS voice short name.
        rate: Speech rate adjustment (e.g. ``"+10%"``).
        pitch: Pitch adjustment (e.g. ``"+2Hz"``).
        proxy: Optional proxy URL forwarded to Edge TTS.

    Returns:
        A list of ``{"text", "start", "end"}`` dicts in chronological order.
    """
    # boundary="WordBoundary" is CRITICAL: the default SentenceBoundary does
    # not emit the per-word offsets we need for precise subtitle syncing.
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        boundary="WordBoundary",
        proxy=proxy,
    )

    audio_chunks: List[bytes] = []
    words: List[Dict[str, Any]] = []

    async for chunk in communicate.stream():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            data = chunk.get("data")
            if data:
                audio_chunks.append(data)
        elif chunk_type == "WordBoundary":
            word_text = str(chunk.get("text", "")).strip()
            if not word_text:
                continue
            offset = int(chunk.get("offset") or 0)
            duration = int(chunk.get("duration") or 0)
            start = offset / _TICKS_PER_SECOND
            end = (offset + duration) / _TICKS_PER_SECOND
            words.append({"text": word_text, "start": start, "end": end})

    parent = os.path.dirname(os.path.abspath(out_mp3))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_mp3, "wb") as handle:
        handle.write(b"".join(audio_chunks))

    return words


def capture_words(
    text: str,
    out_mp3: str,
    voice: str = "en-US-ChristopherNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    proxy: Optional[str] = None,
) -> Dict[str, Any]:
    """Synthesize ``text`` to an MP3 and capture exact word timings.

    Edge TTS reports WordBoundary ``offset``/``duration`` values in 100ns
    ticks; they are converted to floating-point seconds here.

    Args:
        text: Narration text to synthesize.
        out_mp3: Path of the MP3 file to write (parent dirs are created).
        voice: Edge TTS voice short name.
        rate: Rate adjustment string such as ``"+10%"``.
        pitch: Pitch adjustment string such as ``"-2Hz"``.
        proxy: Optional proxy URL for Edge TTS.

    Returns:
        Dict with keys ``audio_path``, ``words``, ``duration_est``, ``voice``
        and ``rate``.  Each word is ``{"text", "start", "end"}`` with times in
        seconds.  ``duration_est`` is the end time of the last word (0.0 if
        no word boundaries were emitted).

    Raises:
        RuntimeError: If Edge TTS synthesis fails, with the voice identified.
    """
    try:
        words = asyncio.run(
            _stream_speech(text, out_mp3, voice, rate, pitch, proxy)
        )
    except Exception as exc:  # noqa: BLE001 - surface a clear, contextual error
        raise RuntimeError(
            f"Edge-TTS narration failed for voice '{voice}': {exc}"
        ) from exc

    duration_est = max((float(w["end"]) for w in words), default=0.0)
    return {
        "audio_path": out_mp3,
        "words": words,
        "duration_est": duration_est,
        "voice": voice,
        "rate": rate,
    }


def make_audition(text: str, out_dir: str) -> Dict[str, Any]:
    """Render a short sample with every voice in :data:`VOICES`.

    A ``audition_manifest.json`` file is written to ``out_dir`` describing
    each rendered sample.

    Args:
        text: Source text; only the first ~200 characters are used.
        out_dir: Directory where mp3 samples and the manifest are written.

    Returns:
        The manifest dict, with a ``voices`` list of entries containing
        ``voice``, ``file``, ``rate``, ``pitch`` and ``description`` (plus an
        ``error`` field if a particular voice failed).
    """
    os.makedirs(out_dir, exist_ok=True)
    sample = text[:200]

    entries: List[Dict[str, Any]] = []
    for label, config in VOICES.items():
        file_name = f"audition_{label}.mp3"
        out_mp3 = os.path.join(out_dir, file_name)
        entry: Dict[str, Any] = {
            "voice": config["name"],
            "file": out_mp3,
            "rate": config["rate"],
            "pitch": config["pitch"],
            "description": config["description"],
        }
        try:
            result = capture_words(
                sample,
                out_mp3,
                voice=config["name"],
                rate=config["rate"],
                pitch=config["pitch"],
            )
            entry["duration_est"] = result["duration_est"]
        except RuntimeError as exc:
            entry["error"] = str(exc)
        entries.append(entry)

    manifest: Dict[str, Any] = {
        "sample_text": sample,
        "voice_count": len(entries),
        "voices": entries,
    }
    manifest_path = os.path.join(out_dir, "audition_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return manifest


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp ``HH:MM:SS,mmm``."""
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(
    words: List[Dict[str, Any]],
    out_path: str,
    group_words: int = 4,
) -> str:
    """Write word timings to a standard SRT subtitle file.

    Consecutive words are grouped into cues of up to ``group_words`` words;
    a cue is also closed early when a word ends in punctuation.

    Args:
        words: Word dicts with ``text``, ``start`` and ``end`` (seconds).
        out_path: Destination ``.srt`` path.
        group_words: Maximum words per cue (values < 1 are treated as 1).

    Returns:
        ``out_path``.
    """
    group_words = max(1, int(group_words))
    cues: List[str] = []
    group: List[Dict[str, Any]] = []

    def flush() -> None:
        if not group:
            return
        start = float(group[0]["start"])
        end = float(group[-1]["end"])
        if end <= start:
            end = start + 0.001
        text = " ".join(str(w["text"]) for w in group).strip()
        cues.append(
            "{}\n{} --> {}\n{}\n".format(
                len(cues) + 1,
                _format_srt_timestamp(start),
                _format_srt_timestamp(end),
                text,
            )
        )
        group.clear()

    for word in words:
        group.append(word)
        token = str(word.get("text", "")).strip()
        if len(group) >= group_words or (
            token and token[-1] in _CUE_END_PUNCTUATION
        ):
            flush()
    flush()

    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(cues))
        if cues:
            handle.write("\n")

    return out_path


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_spoken_lines(text: str) -> List[str]:
    """Split narration into breath-length spoken lines."""
    return [s.strip() for s in _SENTENCE_SPLIT.split((text or "").strip()) if s.strip()]


def make_prosody_profile(sentences: List[str]) -> List[Tuple[str, str, int]]:
    """Return (rate, pitch, pause_ms) for each sentence.

    Small, deliberate variation between sentences is what breaks the flat
    "article reader" cadence.  The first line is brighter, fragments are
    snappy, questions lift, and the last line settles.
    """
    profile: List[Tuple[str, str, int]] = []
    last = len(sentences) - 1
    for index, sentence in enumerate(sentences):
        stripped = sentence.strip()
        short = len(stripped.split()) <= 6
        if index == 0:
            profile.append(("+12%", "+3Hz", 380))
        elif stripped.endswith("?"):
            profile.append(("+2%", "+6Hz", 280))
        elif index == last:
            profile.append(("-6%", "-2Hz", 0))
        elif short:
            profile.append(("+8%", "+1Hz", 130))
        elif index == 1:
            profile.append(("+5%", "+0Hz", 200))
        else:
            profile.append(("+3%", "+0Hz", 170))
    return profile


def _media_duration(path: str) -> float:
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def synthesize_performance(
    text: str,
    out_mp3: str,
    voice: str = "en-US-AvaNeural",
    proxy: Optional[str] = None,
    profile: Optional[List[Tuple[str, str, int]]] = None,
) -> Dict[str, Any]:
    """Synthesize narration sentence-by-sentence with expressive prosody.

    Each sentence gets its own rate/pitch and a short FFmpeg-generated silence
    before the next sentence. Word-boundary timings are offset by the elapsed
    audio so subtitles stay in sync. Returns the same shape as
    :func:`capture_words` plus a ``chunks`` diagnostic list.
    """
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    sentences = split_spoken_lines(text)
    if not sentences:
        raise RuntimeError("No sentences to synthesize")
    prosody = profile or make_prosody_profile(sentences)

    work_dir = Path(out_mp3).parent / "voice_chunks"
    work_dir.mkdir(parents=True, exist_ok=True)
    pieces: List[Path] = []
    words: List[Dict[str, Any]] = []
    elapsed = 0.0
    details: List[Dict[str, Any]] = []

    for index, sentence in enumerate(sentences):
        rate, pitch, pause_ms = prosody[index] if index < len(prosody) else ("+3%", "0Hz", 170)
        chunk_path = work_dir / f"chunk_{index:02d}.mp3"
        try:
            chunk_words = asyncio.run(
                _stream_speech(sentence, str(chunk_path), voice, rate, pitch, proxy)
            )
        except Exception as exc:
            raise RuntimeError(f"Edge-TTS narration failed for voice '{voice}': {exc}") from exc
        chunk_duration = _media_duration(str(chunk_path))
        for word in chunk_words:
            words.append({
                "text": word["text"],
                "start": elapsed + float(word["start"]),
                "end": elapsed + float(word["end"]),
            })
        elapsed += chunk_duration
        pieces.append(chunk_path)
        details.append({
            "index": index, "text": sentence, "rate": rate, "pitch": pitch,
            "pause_ms": pause_ms, "duration": round(chunk_duration, 2),
        })
        if pause_ms > 0 and index < len(sentences) - 1:
            silence_path = work_dir / f"silence_{index:02d}.mp3"
            subprocess.run(
                [ffmpeg, "-y", "-f", "lavfi", "-i",
                 f"anullsrc=r=24000:cl=mono", "-t", f"{pause_ms / 1000:.3f}",
                 "-q:a", "9", str(silence_path)],
                capture_output=True, check=True,
            )
            pieces.append(silence_path)
            elapsed += pause_ms / 1000.0

    concat_list = work_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8"
    )
    Path(out_mp3).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(out_mp3)],
        capture_output=True, check=True,
    )
    return {
        "audio_path": out_mp3,
        "words": words,
        "duration_est": elapsed,
        "voice": voice,
        "rate": "performance",
        "chunks": details,
    }


if __name__ == "__main__":
    # Offline smoke test: exercises the grouping/SRT logic without a network
    # call.  Run ``python -m src.voice --live`` to also test Edge TTS itself.
    import sys

    print(f"Available audition voices: {', '.join(VOICES)}")

    demo_words = [
        {"text": "Hello", "start": 0.0, "end": 0.32},
        {"text": "world,", "start": 0.35, "end": 0.70},
        {"text": "this", "start": 0.75, "end": 0.95},
        {"text": "is", "start": 0.98, "end": 1.10},
        {"text": "a", "start": 1.12, "end": 1.20},
        {"text": "test.", "start": 1.25, "end": 1.80},
    ]
    demo_srt = write_srt(demo_words, "voice_smoke_test.srt", group_words=4)
    print(f"Wrote demo subtitles to {demo_srt}")

    if "--live" in sys.argv:
        result = capture_words(
            "Hello world, this is a test.",
            "voice_smoke_test.mp3",
        )
        print(
            f"Synced {len(result['words'])} words "
            f"(~{result['duration_est']:.2f}s) with {result['voice']}"
        )
