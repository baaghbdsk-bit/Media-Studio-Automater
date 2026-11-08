"""
Scene-Accurate Narration Builder.

Instead of synthesizing one long voiceover blob (which drifts out of sync with
the visuals), this engine talks per scene, measures each clip, and assembles a
timeline where every scene lasts exactly as long as its narration.

Quality upgrades:
- A pronunciation dictionary spells out acronyms the TTS would otherwise mangle
- Per-scene rate/pitch/volume, with audience-aware pacing
- Sentence-boundary timings from edge-tts, so captions follow the real audio
- A moving four-chord ambient bed that ducks under the voice
- A final loudness-normalisation pass (-16 LUFS, -1.5 dBTP)
- A fallback voice if the primary voice fails every retry
"""
import asyncio
import re
import subprocess
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import edge_tts
except Exception:  # pragma: no cover
    edge_tts = None


SAMPLE_RATE = 44100
PAUSE_BETWEEN = 0.34
TAIL_PAD = 0.30

AUDIENCE_RATE = {
    "beginner": "+2%",
    "intermediate": "+6%",
    "advanced": "+8%",
}

# Tokens that edge-tts commonly mispronounces in technical narration.
TOKEN_PRONUNCIATION = {
    "FP8": "F P eight", "FP16": "F P sixteen", "FP32": "F P thirty two",
    "INT8": "int eight", "INT4": "int four", "INT16": "int sixteen",
    "KV": "K V", "QKV": "Q K V", "GQA": "G Q A", "MQA": "M Q A",
    "GPU": "G P U", "GPUs": "G P U S", "CPU": "C P U", "CPUs": "C P U S",
    "LLM": "L L M", "LLMs": "L L M S", "API": "A P I", "APIs": "A P I S",
    "SDK": "S D K", "ORM": "O R M", "SQL": "sequel", "JSON": "jason",
    "YAML": "yammel", "HTTP": "H T T P", "HTTPS": "H T T P S",
    "TLS": "T L S", "DNS": "D N S", "TCP": "T C P", "UDP": "U D P",
    "RAG": "rag", "MoE": "mixture of experts", "LoRA": "Lora",
    "QLoRA": "Q Lora", "vLLM": "V L L M", "HBM": "H B M",
    "SRAM": "S ram", "TMA": "T M A", "GEMM": "gem", "BM25": "B M twenty five",
    "P99": "P ninety nine", "H100": "H one hundred", "A100": "A one hundred",
    "RTX": "R T X", "JWT": "J W T", "OAuth": "O auth", "SSO": "S S O",
    "2FA": "two factor authentication", "SLA": "S L A", "SLO": "S L O",
    "CI": "C I", "CD": "C D", "URL": "U R L", "USB": "U S B",
    "RAM": "ram", "SSD": "S S D", "HDD": "H D D", "OOM": "out of memory",
    "arXiv": "archive", "AI": "A I", "ML": "M L", "ID": "I D",
    "VS": "versus", "vs": "versus", "eg": "for example", "ie": "that is",
}

_PRE_REPLACEMENTS = [
    (r"\bO\(N\s*\^?\s*2\)", "big O of N squared"),
    (r"\bO\(N\s*²\)", "big O of N squared"),
    (r"\bO\(N\s*log\s*N\)", "big O of N log N"),
    (r"O\(([^)]{1,24})\)", r"big O of \1"),
    (r"\b4K\b", "four K"),
    (r"\b1080p\b", "ten eighty P"),
    (r"\b1440p\b", "fourteen forty P"),
    (r"\b2160p\b", "twenty one sixty P"),
    (r"\b4090\b", "forty ninety"),
    (r"\b(\d+)%", r"\1 percent"),
    (r"\s*&\s*", " and "),
    (r"\s*→\s*", " to "),
    (r"\s*←\s*", " from "),
]


def normalize_for_tts(text: str) -> str:
    text = text or ""
    for pattern, replacement in _PRE_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)

    def pronouncer(match: re.Match) -> str:
        token = match.group(0)
        return TOKEN_PRONUNCIATION.get(token, token)

    text = re.sub(r"\b[A-Za-z][A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*\b", pronouncer, text)
    return re.sub(r"\s+", " ", text).strip()


class SceneNarrationBuilder:
    VOICE = "en-US-AndrewMultilingualNeural"
    FALLBACK_VOICE = "en-US-ChristopherNeural"
    RATE = "+6%"

    def __init__(self, fps: int = 30, voice: str = "", rate: str = ""):
        self.fps = fps
        self.voice = voice or self.VOICE
        self.rate = rate or self.RATE

    # ------------------------------------------------------------------ tts
    async def _synth_async(self, text: str, out_path: Path, voice: str,
                           rate: str, pitch: str, volume: str) -> Optional[List[Dict[str, Any]]]:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed")
        communicate = edge_tts.Communicate(
            text, voice, rate=rate, pitch=pitch, volume=volume,
            boundary="SentenceBoundary",
        )
        audio = bytearray()
        sentences: List[Dict[str, Any]] = []
        async for event in communicate.stream():
            kind = event.get("type")
            if kind == "audio":
                audio.extend(event.get("data", b""))
            elif kind == "SentenceBoundary":
                offset = float(event.get("offset", 0)) / 1e7
                duration = float(event.get("duration", 0)) / 1e7
                sentences.append({
                    "text": str(event.get("text") or "").strip(),
                    "start": offset,
                    "end": offset + duration,
                })
        if len(audio) > 500:
            out_path.write_bytes(bytes(audio))
            return sentences
        return None

    def _synth_scene(self, text: str, out_path: Path, voice: str,
                     rate: str, pitch: str, volume: str) -> Optional[List[Dict[str, Any]]]:
        spoken = normalize_for_tts(text)
        for attempt in range(4):
            try:
                sentences = asyncio.run(
                    self._synth_async(spoken, out_path, voice, rate, pitch, volume))
                if sentences is not None:
                    return sentences
                print(f"[Narration] TTS attempt {attempt + 1} returned no audio", flush=True)
            except Exception as exc:
                print(f"[Narration] TTS attempt {attempt + 1} failed: {exc}", flush=True)
            time.sleep(1.5 * (attempt + 1))

        if voice != self.FALLBACK_VOICE:
            try:
                sentences = asyncio.run(
                    self._synth_async(spoken, out_path, self.FALLBACK_VOICE, rate, pitch, volume))
                if sentences is not None:
                    print(f"[Narration] Recovered with fallback voice {self.FALLBACK_VOICE}", flush=True)
                    return sentences
            except Exception as exc:
                print(f"[Narration] Fallback voice failed: {exc}", flush=True)
        return None

    # ------------------------------------------------------------------ pcm
    def _decode_pcm(self, path: Path) -> np.ndarray:
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", str(path),
            "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0

    def _estimate_seconds(self, text: str) -> float:
        words = max(1, len(text.split()))
        return max(3.0, words / 2.45 + 0.8)

    # --------------------------------------------------------------- music
    def _ambient_bed(self, num_samples: int) -> np.ndarray:
        """Soft cinematic pad that walks Am-F-C-G, with no chord-boundary clicks."""
        n = max(1, num_samples)
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE

        chords = [
            [(110.00, 0.26), (164.81, 0.14), (220.00, 0.12), (261.63, 0.08), (329.63, 0.05)],
            [(87.31, 0.26), (130.81, 0.14), (174.61, 0.12), (220.00, 0.08), (261.63, 0.05)],
            [(130.81, 0.26), (196.00, 0.14), (261.63, 0.12), (329.63, 0.08), (392.00, 0.05)],
            [(98.00, 0.26), (146.83, 0.14), (196.00, 0.12), (246.94, 0.08), (293.66, 0.05)],
        ]
        segment = int(SAMPLE_RATE * 7.5)
        fade = int(SAMPLE_RATE * 1.8)
        pad = np.zeros(n, dtype=np.float64)
        pos = 0
        chord_index = 0

        while pos < n:
            length = min(segment + fade, n - pos)
            tt = np.arange(length, dtype=np.float64) / SAMPLE_RATE
            chunk = np.zeros(length, dtype=np.float64)
            for freq, amp in chords[chord_index % len(chords)]:
                detune = 1.0 + 0.0016 * np.sin(2 * np.pi * 0.05 * tt + freq)
                chunk += amp * np.sin(2 * np.pi * freq * tt * detune)
            env = np.ones(length, dtype=np.float64)
            f_in = min(fade, length)
            f_out = min(fade, length)
            env[:f_in] *= np.linspace(0.0, 1.0, f_in)
            env[-f_out:] *= np.linspace(1.0, 0.0, f_out)
            pad[pos:pos + length] += chunk * env
            if n - pos <= segment + fade:
                break
            pos += segment
            chord_index += 1

        tremolo = 0.88 + 0.12 * np.sin(2 * np.pi * 0.075 * t)
        pad *= tremolo

        rng = np.random.default_rng(7)
        noise = rng.standard_normal(n).astype(np.float64) * 0.012
        kernel = np.ones(48) / 48.0
        pad += np.convolve(noise, kernel, mode="same")

        fade_in = min(int(SAMPLE_RATE * 2.0), n)
        fade_out = min(int(SAMPLE_RATE * 3.0), n)
        if fade_in:
            pad[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
        if fade_out:
            pad[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)

        peak = float(np.max(np.abs(pad))) or 1.0
        return (pad / peak * 0.28).astype(np.float32)

    def _ducking_envelope(self, voice: np.ndarray) -> np.ndarray:
        window = max(1, int(SAMPLE_RATE * 0.05))
        env = np.convolve(np.abs(voice), np.ones(window) / window, mode="same")
        peak = float(np.max(env)) or 1.0
        return np.clip(env / peak, 0.0, 1.0)

    # ---------------------------------------------------------------- build
    def build(self, storyboard: Dict[str, Any], work_dir: Path) -> Dict[str, Any]:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        scenes: List[Dict[str, Any]] = storyboard.get("scenes", [])
        if not scenes:
            raise RuntimeError("Storyboard has no scenes to narrate")

        audience = str(storyboard.get("audience") or "beginner").lower()
        default_rate = AUDIENCE_RATE.get(audience, self.rate)

        clips: List[np.ndarray] = []
        durations: List[float] = []
        scene_sentences: List[List[Dict[str, Any]]] = []
        failed = 0

        for i, sc in enumerate(scenes):
            text = (sc.get("narration_segment") or "").strip()
            if not text:
                text = f"{sc.get('title', '')}. {sc.get('caption', '')}".strip()
            if not text:
                text = f"Scene {i + 1}"

            mp3_path = work_dir / f"narration_scene_{i + 1}.mp3"
            sentences = self._synth_scene(
                text,
                mp3_path,
                str(sc.get("voice") or self.voice),
                str(sc.get("rate") or default_rate),
                str(sc.get("pitch") or "+0Hz"),
                str(sc.get("volume") or "+0%"),
            )
            if sentences is not None:
                pcm = self._decode_pcm(mp3_path)
                dur = len(pcm) / SAMPLE_RATE
                print(f"[Narration] Scene {i + 1}: {dur:.2f}s ({len(sentences)} sentences)", flush=True)
            else:
                failed += 1
                dur = self._estimate_seconds(text)
                pcm = np.zeros(int(dur * SAMPLE_RATE), dtype=np.float32)
                sentences = []
                print(f"[Narration] Scene {i + 1}: TTS failed, using {dur:.2f}s silence", flush=True)

            clips.append(pcm)
            durations.append(dur)
            scene_sentences.append(sentences)

        if failed == len(scenes):
            raise RuntimeError(
                "Edge TTS failed for every scene after retries; refusing to publish a silent video"
            )

        pieces: List[np.ndarray] = []
        scene_spans: List[float] = []
        cursor = 0.0
        for i, pcm in enumerate(clips):
            requested = scenes[i].get("pause_after")
            pause_after = float(requested) if requested is not None else (
                PAUSE_BETWEEN if i < len(clips) - 1 else TAIL_PAD)
            span = pcm.size / SAMPLE_RATE + pause_after
            scene_spans.append(span)
            pieces.append(pcm)
            pieces.append(np.zeros(int(pause_after * SAMPLE_RATE), dtype=np.float32))
            cursor += span

        total_samples = int(round(cursor * SAMPLE_RATE))
        voice = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        if voice.size < total_samples:
            voice = np.pad(voice, (0, total_samples - voice.size))
        elif voice.size > total_samples:
            voice = voice[:total_samples]

        total_duration = total_samples / SAMPLE_RATE

        # Bake exact fractions, then attach real sentence timings (local to each
        # scene) so the subtitle generator does not have to estimate them.
        for sc, span, sentences, pcm in zip(scenes, scene_spans, scene_sentences, clips):
            sc["fraction"] = span / total_duration
            audio_span = pcm.size / SAMPLE_RATE
            sc["_sentence_timings"] = [
                {
                    "text": s["text"],
                    "start": max(0.0, min(float(s["start"]), audio_span)),
                    "end": max(0.0, min(float(s["end"]), audio_span)),
                }
                for s in sentences
            ]

        samples_per_frame = int(SAMPLE_RATE / self.fps)
        total_frames = max(1, int(round(total_duration * self.fps)))
        visemes: List[float] = []
        for f in range(total_frames):
            a = f * samples_per_frame
            b = min(a + samples_per_frame, voice.size)
            chunk = voice[a:b]
            rms = float(np.sqrt(np.mean(chunk ** 2))) if chunk.size else 0.0
            visemes.append(min(1.0, rms * 6.0))

        bed = self._ambient_bed(total_samples)
        duck = self._ducking_envelope(voice)
        music_gain = 0.18 * (1.0 - 0.68 * duck)

        left = np.clip(voice + np.roll(bed, 240) * music_gain, -1.0, 1.0)
        right = np.clip(voice + bed * music_gain, -1.0, 1.0)
        stereo = np.stack([left, right], axis=1)

        raw_path = work_dir / "narration_raw.wav"
        pcm16 = (stereo * 32767.0).astype(np.int16)
        with wave.open(str(raw_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm16.tobytes())

        audio_path = work_dir / "narration.wav"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-i", str(raw_path),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:linear=true",
                    "-ar", str(SAMPLE_RATE), "-ac", "2", str(audio_path),
                ],
                check=True,
            )
        except Exception as exc:
            print(f"[Narration] Loudness normalisation skipped: {exc}", flush=True)
            audio_path = raw_path

        print(
            f"[Narration] Voiceover ready: {total_duration:.1f}s, {total_frames} frames "
            f"@ {self.fps}fps (-16 LUFS)",
            flush=True,
        )

        return {
            "audio_path": str(audio_path),
            "duration": total_duration,
            "total_frames": total_frames,
            "visemes": visemes,
        }
