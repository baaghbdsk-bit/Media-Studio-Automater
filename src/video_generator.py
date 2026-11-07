import sys
import os
import asyncio
import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import edge_tts
from playwright.sync_api import sync_playwright
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from src.manim_generator import generate_short_manim_code, generate_explainer_manim_code

class VideoGenerator:
    """
    Primary Animation Studio Engine using Manim Community Edition.
    Generates genuine, high-production 3Blue1Brown-style mathematical & algorithmic animations:
    - 9:16 Vertical (1080x1920) for YouTube Shorts, Instagram Reels, Pinterest Video Pins
    - 16:9 Landscape (1920x1080) for Alternate-Day YouTube Long-Form Explainers
    - Neural TTS Voiceover (Edge-TTS en-US-AndrewMultilingualNeural)
    - Synced Subtitles (.srt) and dynamic audio mixing via FFmpeg
    """

    VOICE = "en-US-AndrewMultilingualNeural"
    RATE = "+10%"

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.output_dir = self.base_dir / "generated_visuals" / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_path = self.base_dir / "src" / "templates" / "animated_short_template.html"

    async def _synthesize_speech(self, script_text: str, output_audio: str):
        communicate = edge_tts.Communicate(script_text, self.VOICE, rate=self.RATE)
        await communicate.save(output_audio)

    def _get_audio_duration(self, audio_path: str) -> float:
        """Determines duration in seconds of the synthesized audio file."""
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return float(data.get("format", {}).get("duration", 42.0))
        except Exception:
            pass
        return 42.0

    def _render_manim(self, manim_code: str, scene_name: str, output_dir: Path, quality: str = "-qm") -> Optional[str]:
        """Renders Manim animation and returns path to output MP4."""
        script_file = output_dir / "manim_scene.py"
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(manim_code)

        media_dir = output_dir / "manim_media"
        media_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "-m", "manim",
            str(script_file),
            scene_name,
            quality,
            "--media_dir", str(media_dir)
        ]

        print(f"[VideoGenerator] 🎬 Rendering Manim scene '{scene_name}' with Manim Community...")
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=400, cwd=str(output_dir))
            if proc.returncode != 0:
                print(f"[VideoGenerator] Manim render note: {proc.stderr[-300:] if proc.stderr else ''}")
                return None

            # Search for rendered MP4
            for mp4 in media_dir.rglob("*.mp4"):
                if "partial_movie_files" not in str(mp4) and mp4.stat().st_size > 50000:
                    print(f"[VideoGenerator] ✅ Manim raw animation ready: {mp4.name} ({round(mp4.stat().st_size/1024, 1)} KB)")
                    return str(mp4)
        except Exception as ex:
            print(f"[VideoGenerator] Manim execution note: {ex}")
        return None

    def _merge_video_audio(self, video_path: str, audio_path: str, output_path: str, max_duration: float = 58.0) -> bool:
        """Fast FFmpeg audio-video merging."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-t", f"{max_duration:.2f}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path)
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
            return Path(output_path).exists() and Path(output_path).stat().st_size > 50000
        except Exception as ex:
            print(f"[VideoGenerator] FFmpeg merge note: {ex}")
            return False

    def _generate_srt_file(self, scenes: List[Dict[str, Any]], srt_path: str):
        """Builds standard SubRip (.srt) subtitle track for YouTube Captions."""
        def format_timestamp(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int(round((seconds - int(seconds)) * 1000))
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

        srt_blocks = []
        current_time = 0.0
        for i, scene in enumerate(scenes, 1):
            dur = float(scene.get("duration", 10.0))
            start_str = format_timestamp(current_time)
            end_str = format_timestamp(current_time + dur)
            caption = scene.get("caption", "").strip()
            srt_blocks.append(f"{i}\n{start_str} --> {end_str}\n{caption}\n")
            current_time += dur

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_blocks))

    def generate_dynamic_short(self, topic_data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Optional[str]]:
        """
        Renders a full-production 9:16 Vertical (1080x1920) Manim Animation Short/Reel.
        Strictly clamped <= 58s for YouTube Shorts & Instagram Reels compliance.
        """
        title = topic_data.get("title", "AI Breakthrough")
        summary = topic_data.get("summary", "Understanding modern artificial intelligence systems.")
        problem = topic_data.get("problem", "Traditional models run into compute bottlenecks.")
        solution = topic_data.get("solution", "Dynamic routing and memory optimization accelerate throughput.")
        pro_tip = topic_data.get("pro_tip", "Always benchmark real latency on live workloads.")
        narration = topic_data.get("narration")

        if not narration or len(narration.split()) < 50:
            narration = (
                f"In this engineering breakdown, we analyze {title}. "
                f"{summary}. "
                f"Why does this matter so much for production deployments? "
                f"Under conventional architectures, {problem}. Memory transfer creates a severe latency bottleneck. "
                f"The core technical unlock is {solution}. This achieves dramatic acceleration without degrading precision. "
                f"Here is your production engineering rule: {pro_tip}. "
                f"To inspect live latency, memory, and token economics across 260-plus frontier models, explore NeuBench at app.neubench.workers.dev."
            )

        slug = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')[:35]
        video_dir = self.output_dir / slug
        video_dir.mkdir(parents=True, exist_ok=True)

        audio_path = str(video_dir / "narration.mp3")
        video_path = str(video_dir / f"manim_short_{slug}.mp4")
        srt_path = str(video_dir / f"subtitles_{slug}.srt")

        if dry_run:
            if not Path(video_path).exists():
                Path(video_path).touch()
            return {
                "video_path": video_path,
                "srt_path": srt_path,
                "audio_path": audio_path
            }

        try:
            # 1. Synthesize voiceover with Edge TTS
            print(f"[VideoGenerator] Generating neural voiceover for: '{title[:40]}'...")
            async def _synth():
                await self._synthesize_speech(narration, audio_path)
            asyncio.run(asyncio.wait_for(_synth(), timeout=60.0))

            # 2. Measure audio duration and clamp to <= 58.0s
            audio_dur = self._get_audio_duration(audio_path)
            total_dur = min(max(audio_dur, 30.0), 58.0)
            print(f"[VideoGenerator] Target Short duration: {total_dur:.1f}s (Audio: {audio_dur:.1f}s)")

            # 3. Generate SRT subtitle file
            sub_scenes = [
                {"duration": total_dur * 0.25, "caption": f"{title} Explained"},
                {"duration": total_dur * 0.25, "caption": "The Core Compute Bottleneck"},
                {"duration": total_dur * 0.30, "caption": "The Architectural Unlock"},
                {"duration": total_dur * 0.20, "caption": "Production Rule & NeuBench"}
            ]
            self._generate_srt_file(sub_scenes, srt_path)

            # 4. Generate & Render 9:16 Manim Scene
            manim_code = generate_short_manim_code(topic_data, target_duration=total_dur)
            raw_video = self._render_manim(manim_code, "ShortExplainerScene", video_dir, quality="-qm")

            # 5. Merge Manim Animation with Voiceover Audio
            if raw_video and Path(raw_video).exists():
                print(f"[VideoGenerator] Merging Manim animation with neural voiceover via FFmpeg...")
                ok = self._merge_video_audio(raw_video, audio_path, video_path, max_duration=total_dur)
                if ok and Path(video_path).stat().st_size > 50000:
                    print(f"[VideoGenerator] 🚀 Professional Manim Short complete: {video_path}")
                    return {
                        "video_path": video_path,
                        "srt_path": srt_path,
                        "audio_path": audio_path
                    }

        except Exception as ex:
            print(f"[VideoGenerator] Manim pipeline note: {ex}")

        # Fallback to touch if dry-run or error
        return {"video_path": video_path if Path(video_path).exists() else None, "srt_path": srt_path, "audio_path": audio_path}

    def generate_dynamic_explainer(self, topic_data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Optional[str]]:
        """
        Renders a full 16:9 Landscape (1920x1080) Manim Long-Form Explainer Video for YouTube.
        Duration: 3 to 5 minutes with chapters and mathematical derivations.
        """
        title = topic_data.get("title", "Frontier AI Architecture")
        summary = topic_data.get("summary", "Complete engineering breakdown of frontier AI architectures.")
        problem = topic_data.get("problem", "Memory bandwidth and parameter scaling bottlenecks.")
        solution = topic_data.get("solution", "Mathematical formulation and architectural decomposition.")
        pro_tip = topic_data.get("pro_tip", "Production rules for scaling and deployment.")

        slug = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')[:35]
        video_dir = self.output_dir / f"explainer_{slug}"
        video_dir.mkdir(parents=True, exist_ok=True)

        audio_path = str(video_dir / "explainer_narration.mp3")
        video_path = str(video_dir / f"youtube_explainer_{slug}.mp4")
        srt_path = str(video_dir / f"explainer_subtitles_{slug}.srt")

        if dry_run:
            if not Path(video_path).exists():
                Path(video_path).touch()
            return {
                "video_path": video_path,
                "srt_path": srt_path,
                "audio_path": audio_path,
                "chapters": ["00:00 Introduction", "01:00 Mathematical Formulation", "02:30 Production Benchmarks"]
            }

        try:
            # Long-form comprehensive narration
            long_narration = (
                f"Welcome to this technical deep-dive on {title}. "
                f"{summary}. "
                f"To truly understand why this breakthrough is critical, we first need to confront the core limitation of modern scale. "
                f"Under conventional architectures, {problem}. As sequence length increases, memory bandwidth rather than raw compute becomes the hard physical bottleneck. "
                f"Now let us examine the mathematical unlock. {solution}. "
                f"Notice how the decomposition restructures memory access patterns, slashing the memory footprint while preserving model expressivity. "
                f"When deploying these architectures to production, here is your essential engineering takeaway: {pro_tip}. "
                f"For live token economics, throughput benchmarks, and latency comparisons across 260 frontier AI models, explore NeuBench at app.neubench.workers.dev."
            )

            print(f"[VideoGenerator] Synthesizing Long-Form Explainer narration...")
            async def _synth():
                await self._synthesize_speech(long_narration, audio_path)
            asyncio.run(asyncio.wait_for(_synth(), timeout=120.0))

            audio_dur = self._get_audio_duration(audio_path)
            total_dur = max(audio_dur, 60.0)
            print(f"[VideoGenerator] Explainer duration: {total_dur:.1f}s")

            # Generate 16:9 Widescreen Manim Scene
            manim_code = generate_explainer_manim_code(topic_data, target_duration=total_dur)
            raw_video = self._render_manim(manim_code, "LongExplainerScene", video_dir, quality="-qm")

            if raw_video and Path(raw_video).exists():
                ok = self._merge_video_audio(raw_video, audio_path, video_path, max_duration=total_dur)
                if ok and Path(video_path).stat().st_size > 100000:
                    print(f"[VideoGenerator] 🎬 16:9 YouTube Long Explainer complete: {video_path}")
                    return {
                        "video_path": video_path,
                        "srt_path": srt_path,
                        "audio_path": audio_path,
                        "chapters": [
                            "00:00 Introduction & The Scaling Dilemma",
                            "01:10 Mathematical Formulation & Architecture",
                            "02:40 Production Benchmarks on NeuBench"
                        ]
                    }
        except Exception as ex:
            print(f"[VideoGenerator] Long explainer error: {ex}")

        return {"video_path": video_path if Path(video_path).exists() else None, "srt_path": srt_path, "audio_path": audio_path}
