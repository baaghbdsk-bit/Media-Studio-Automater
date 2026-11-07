"""
Audio Producer
Handles voiceover (Edge TTS), background music, and sound effects mixing.
"""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import edge_tts

from src.video_config import (
    AUDIO_OUTPUT_DIR,
    BASE_DIR,
    TTS_RATE,
    TTS_PITCH,
    TTS_VOICE,
)


class AudioProducer:
    def __init__(self, output_root: Optional[Path] = None):
        self.output_root = output_root or AUDIO_OUTPUT_DIR
        self.output_root.mkdir(parents=True, exist_ok=True)

    async def _synthesize_speech(
        self,
        text: str,
        output_path: Path,
        voice: str = TTS_VOICE,
        rate: str = TTS_RATE,
        pitch: str = TTS_PITCH,
    ) -> bool:
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            print(f"[AudioProducer] TTS error: {e}")
            return False

    def generate_voiceover(
        self,
        text: str,
        output_name: str = "narration",
        voice: str = TTS_VOICE,
        rate: str = TTS_RATE,
    ) -> Dict[str, Any]:
        output_path = self.output_root / f"{output_name}.wav"

        try:
            asyncio.run(self._synthesize_speech(text, output_path, voice, rate))
        except Exception as e:
            return {
                "success": False,
                "error": f"TTS generation failed: {e}",
                "audio_path": None,
                "duration": None,
            }

        if not output_path.exists():
            return {
                "success": False,
                "error": "Audio file was not created",
                "audio_path": None,
                "duration": None,
            }

        duration = self._get_audio_duration(output_path)

        return {
            "success": True,
            "audio_path": str(output_path),
            "duration": duration,
            "voice": voice,
            "rate": rate,
        }

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            proc = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            data = json.loads(proc.stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return 0.0

    def mix_audio(
        self,
        voiceover_path: Path,
        music_path: Optional[Path] = None,
        output_name: str = "final_audio",
        voice_volume: float = 1.0,
        music_volume: float = 0.15,
    ) -> Dict[str, Any]:
        output_path = self.output_root / f"{output_name}.wav"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(voiceover_path),
        ]

        if music_path and music_path.exists():
            cmd.extend(["-i", str(music_path)])
            cmd.extend([
                "-filter_complex",
                f"[0:a]volume={voice_volume}[voice];[1:a]volume={music_volume}[music];[voice][music]amix=inputs=2:duration=first[aout]",
                "-map", "[aout]",
            ])
        else:
            cmd.extend([
                "-filter_complex", f"[0:a]volume={voice_volume}[aout]",
                "-map", "[aout]",
            ])

        cmd.extend([
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            str(output_path),
        ])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                return {
                    "success": False,
                    "error": f"Audio mix failed: {proc.stderr[-500:]}",
                    "audio_path": None,
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "audio_path": None,
            }

        duration = self._get_audio_duration(output_path)

        return {
            "success": True,
            "audio_path": str(output_path),
            "duration": duration,
        }

    def generate_background_music(
        self,
        duration: float,
        output_name: str = "background_music",
        frequency_hz: float = 110.0,
        volume: float = 0.03,
    ) -> Optional[Path]:
        output_path = self.output_root / f"{output_name}.mp3"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={frequency_hz}:duration={duration}",
            "-f", "lavfi",
            "-i", f"sine=frequency={frequency_hz * 1.5}:duration={duration}",
            "-filter_complex",
            f"[0][1]amix=inputs=2:duration=first,volume={volume},afade=t=in:d=2,afade=t=out:st={duration-2}:d=2",
            "-c:a", "libmp3lame",
            "-q:a", "5",
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if output_path.exists():
                return output_path
        except Exception:
            pass

        return None