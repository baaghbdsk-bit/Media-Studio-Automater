"""
Audio & Viseme Lip-Sync Engine for 3D Presenter.
Synthesizes neural voiceover via Edge-TTS and calculates exact 30fps
frame-by-frame mouth-opening (viseme) values from RMS audio energy.
"""
import asyncio
import json
import subprocess
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple

import edge_tts


class AudioLipSyncEngine:
    VOICE = "en-US-AndrewMultilingualNeural"
    RATE = "+8%"
    SAMPLE_RATE = 44100
    FPS = 30

    def __init__(self, output_dir: Path, fps: int = 24):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.FPS = fps

    async def _synth(self, text: str, output_path: Path):
        communicate = edge_tts.Communicate(text, self.VOICE, rate=self.RATE)
        await communicate.save(str(output_path))

    def generate_narration_and_visemes(
        self, script_text: str, filename_prefix: str = "narration"
    ) -> Dict[str, Any]:
        """
        Synthesizes audio and extracts a frame-by-frame viseme array (30 fps)
        with values ranging from 0.0 (closed mouth) to 1.0 (wide open).
        """
        audio_path = self.output_dir / f"{filename_prefix}.mp3"
        print(f"[LipSyncEngine] Synthesizing neural voiceover with Edge-TTS...", flush=True)

        asyncio.run(self._synth(script_text, audio_path))

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError(f"Audio file failed to generate: {audio_path}")

        # Extract duration
        duration = self._get_duration(audio_path)
        total_frames = int(round(duration * self.FPS))
        print(f"[LipSyncEngine] Audio duration: {duration:.2f}s ({total_frames} frames @ {self.FPS}fps)", flush=True)

        # Decode raw PCM audio using FFmpeg
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(audio_path),
            "-f", "s16le",
            "-ac", "1",
            "-ar", str(self.SAMPLE_RATE),
            "-"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        raw_pcm = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0

        samples_per_frame = int(self.SAMPLE_RATE / self.FPS)
        visemes = []

        # Calculate RMS energy for each 30fps frame bucket
        for f in range(total_frames):
            start_idx = f * samples_per_frame
            end_idx = min(start_idx + samples_per_frame, len(raw_pcm))
            if start_idx >= len(raw_pcm):
                visemes.append(0.0)
                continue

            chunk = raw_pcm[start_idx:end_idx]
            rms = np.sqrt(np.mean(chunk**2)) if len(chunk) > 0 else 0.0
            visemes.append(float(rms))

        # Dynamic normalization with speech floor and ceiling
        v_arr = np.array(visemes)
        silence_thresh = 0.015
        max_energy = np.percentile(v_arr[v_arr > silence_thresh], 95) if np.any(v_arr > silence_thresh) else 0.1
        max_energy = max(max_energy, 0.05)

        normalized_visemes = []
        for v in visemes:
            if v < silence_thresh:
                normalized_visemes.append(0.0)
            else:
                norm = min(max((v - silence_thresh) / (max_energy - silence_thresh), 0.0), 1.0)
                # Apply non-linear curve for natural speech mouth-flap
                shaped = float(np.power(norm, 0.85))
                normalized_visemes.append(round(shaped, 3))

        # Apply smoothing so mouth movement is fluid, not jittery
        smoothed = []
        for i in range(len(normalized_visemes)):
            window = normalized_visemes[max(0, i-1) : min(len(normalized_visemes), i+2)]
            smoothed.append(round(float(np.mean(window)), 3))

        return {
            "audio_path": str(audio_path),
            "duration": duration,
            "total_frames": total_frames,
            "visemes": smoothed
        }

    def _get_duration(self, audio_path: Path) -> float:
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio_path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
            )
            data = json.loads(res.stdout)
            return float(data.get("format", {}).get("duration", 60.0))
        except Exception:
            return 60.0
