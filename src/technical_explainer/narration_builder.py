"""
Scene-Accurate Narration Builder.

Instead of synthesizing one long voiceover blob (which drifts out of sync with
the visuals), this engine talks per scene, measures each clip, and assembles a
timeline where every scene lasts exactly as long as its narration. It also
renders visemes per frame and lays a quiet, cinematic ambient bed under the
voice.
"""
import asyncio
import json
import subprocess
import time
import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

try:
    import edge_tts
except Exception:  # pragma: no cover
    edge_tts = None


SAMPLE_RATE = 44100
PAUSE_BETWEEN = 0.34
TAIL_PAD = 0.30


class SceneNarrationBuilder:
    VOICE = "en-US-AndrewMultilingualNeural"
    RATE = "+8%"

    def __init__(self, fps: int = 30, voice: str = "", rate: str = ""):
        self.fps = fps
        self.voice = voice or self.VOICE
        self.rate = rate or self.RATE

    # ------------------------------------------------------------------ tts
    async def _synth_one(self, text: str, out_path: Path) -> None:
        if edge_tts is None:
            raise RuntimeError("edge-tts is not installed")
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(str(out_path))

    def _synth_scene(self, text: str, out_path: Path) -> bool:
        for attempt in range(4):
            try:
                asyncio.run(self._synth_one(text, out_path))
                if out_path.exists() and out_path.stat().st_size > 500:
                    return True
            except Exception as exc:
                print(f"[Narration] TTS attempt {attempt + 1} failed: {exc}", flush=True)
            time.sleep(1.5 * (attempt + 1))
        return False

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
        """Soft, cinematic A-minor pad. Continuous (no chord-boundary clicks)."""
        n = max(1, num_samples)
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE

        partials = [
            (110.00, 0.30),   # A2 root
            (164.81, 0.17),   # E3 fifth
            (220.00, 0.14),   # A3
            (261.63, 0.09),   # C4 minor third
            (329.63, 0.05),   # E4
        ]
        pad = np.zeros(n, dtype=np.float64)
        for freq, amp in partials:
            detune = 1.0 + 0.0016 * np.sin(2 * np.pi * 0.05 * t + freq)
            phase = 2 * np.pi * freq * t * detune
            pad += amp * np.sin(phase)

        tremolo = 0.86 + 0.14 * np.sin(2 * np.pi * 0.075 * t)
        pad *= tremolo

        # very low-level filtered noise wash for texture
        rng = np.random.default_rng(7)
        noise = rng.standard_normal(n).astype(np.float64) * 0.012
        kernel = np.ones(48) / 48.0
        noise = np.convolve(noise, kernel, mode="same")
        pad += noise

        # fades
        fade_in = int(SAMPLE_RATE * 2.0)
        fade_out = int(SAMPLE_RATE * 3.0)
        env = np.ones(n, dtype=np.float64)
        fi = min(fade_in, n)
        fo = min(fade_out, n)
        env[:fi] = np.linspace(0.0, 1.0, fi)
        if fo > 0:
            env[-fo:] = np.linspace(1.0, 0.0, fo)
        pad *= env

        peak = float(np.max(np.abs(pad))) or 1.0
        return (pad / peak * 0.28).astype(np.float32)

    # ---------------------------------------------------------------- build
    def build(self, storyboard: Dict[str, Any], work_dir: Path) -> Dict[str, Any]:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        scenes: List[Dict[str, Any]] = storyboard.get("scenes", [])
        if not scenes:
            raise RuntimeError("Storyboard has no scenes to narrate")

        clips: List[np.ndarray] = []
        durations: List[float] = []
        failed = 0

        for i, sc in enumerate(scenes):
            text = (sc.get("narration_segment") or "").strip()
            if not text:
                text = f"{sc.get('title', '')}. {sc.get('caption', '')}".strip()
            if not text:
                text = f"Scene {i + 1}"

            mp3_path = work_dir / f"narration_scene_{i + 1}.mp3"
            ok = self._synth_scene(text, mp3_path)
            if ok:
                pcm = self._decode_pcm(mp3_path)
                dur = len(pcm) / SAMPLE_RATE
                print(f"[Narration] Scene {i + 1}: {dur:.2f}s", flush=True)
            else:
                failed += 1
                dur = self._estimate_seconds(text)
                pcm = np.zeros(int(dur * SAMPLE_RATE), dtype=np.float32)
                print(f"[Narration] Scene {i + 1}: TTS failed, using {dur:.2f}s silence", flush=True)

            clips.append(pcm)
            durations.append(dur)

        if failed == len(scenes):
            raise RuntimeError(
                "Edge TTS failed for every scene after retries; refusing to publish a silent video"
            )

        # assemble voice timeline with pauses
        pieces: List[np.ndarray] = []
        scene_spans: List[float] = []
        cursor = 0
        for i, pcm in enumerate(clips):
            pause_after = PAUSE_BETWEEN if i < len(clips) - 1 else TAIL_PAD
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

        # bake fractions so visuals last exactly as long as the voice
        for sc, span in zip(scenes, scene_spans):
            sc["fraction"] = span / total_duration

        # visemes (kept for compatibility / optional use)
        samples_per_frame = int(SAMPLE_RATE / self.fps)
        total_frames = max(1, int(round(total_duration * self.fps)))
        visemes: List[float] = []
        for f in range(total_frames):
            a = f * samples_per_frame
            b = min(a + samples_per_frame, voice.size)
            chunk = voice[a:b]
            rms = float(np.sqrt(np.mean(chunk ** 2))) if chunk.size else 0.0
            visemes.append(min(1.0, rms * 6.0))

        # mix ambient bed under the voice
        bed = self._ambient_bed(total_samples)
        voice_gain = 1.0
        music_gain = 0.16
        mixed = np.clip(voice * voice_gain + bed * music_gain, -1.0, 1.0)

        # gentle stereo width on the music side only
        left = np.clip(voice + np.roll(bed, 240) * music_gain, -1.0, 1.0)
        right = np.clip(voice + bed * music_gain, -1.0, 1.0)
        stereo = np.stack([left, right], axis=1)

        wav_path = work_dir / "narration.wav"
        pcm16 = (stereo * 32767.0).astype(np.int16)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm16.tobytes())

        print(f"[Narration] Voiceover ready: {total_duration:.1f}s, {total_frames} frames @ {self.fps}fps", flush=True)

        return {
            "audio_path": str(wav_path),
            "duration": total_duration,
            "total_frames": total_frames,
            "visemes": visemes,
        }
