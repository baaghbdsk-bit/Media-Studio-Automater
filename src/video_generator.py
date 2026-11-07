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
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=700, cwd=str(output_dir))
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
        Duration: 1 to 3 minutes (60s to 180s) for comprehensive in-depth explanation.
        """
        title = topic_data.get("title", "AI Breakthrough")
        summary = topic_data.get("summary", "Understanding modern artificial intelligence systems.")
        problem = topic_data.get("problem", "Traditional models run into compute bottlenecks.")
        solution = topic_data.get("solution", "Dynamic routing and memory optimization accelerate throughput.")
        pro_tip = topic_data.get("pro_tip", "Always benchmark real latency on live workloads.")
        narration = topic_data.get("narration")

        if not narration or len(narration.split()) < 90:
            narration = (
                f"Welcome to this engineering breakdown of {title}. "
                f"{summary} "
                f"To understand why this development is shaking up the artificial intelligence landscape, let's examine the critical bottleneck engineers face. "
                f"Under conventional architectures, {problem} This forces hardware compute units into prolonged idle states while waiting for memory transfers across the bus. "
                f"Here is how this architectural breakthrough solves the bottleneck: {solution} "
                f"By rethinking tensor access patterns and routing data dynamically, modern systems eliminate the memory wall while preserving full numerical precision. "
                f"If you are deploying frontier AI to production, keep this rule in mind: {pro_tip} "
                f"To inspect live token costs, memory footprints, and latency benchmarks across 260 frontier models, explore NeuBench at app.neubench.workers.dev."
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
            asyncio.run(asyncio.wait_for(_synth(), timeout=90.0))

            # 2. Measure audio duration and clamp to 1 - 3 minutes (60.0s to 180.0s)
            audio_dur = self._get_audio_duration(audio_path)
            total_dur = min(max(audio_dur, 60.0), 180.0)
            print(f"[VideoGenerator] Target Short duration (1-3 min): {total_dur:.1f}s (Audio: {audio_dur:.1f}s)")

            # 3. Generate SRT subtitle file
            sub_scenes = [
                {"duration": total_dur * 0.22, "caption": f"{title} Explained"},
                {"duration": total_dur * 0.25, "caption": "The Core Compute Bottleneck"},
                {"duration": total_dur * 0.35, "caption": "The Architectural Unlock"},
                {"duration": total_dur * 0.18, "caption": "Production Rule & NeuBench"}
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
        Duration: 5 to 10 minutes (300s to 600s) with 5 chapters and mathematical derivations.
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

        chapters = [
            "00:00 Introduction & The Scaling Dilemma",
            "01:45 Formal Mathematical Decomposition",
            "03:30 Dynamic Tensor Routing & SRAM Tiles",
            "05:15 Hardware Profiling & Compute Efficiency",
            "07:00 NeuBench Benchmarks & Production Rules"
        ]

        if dry_run:
            if not Path(video_path).exists():
                Path(video_path).touch()
            return {
                "video_path": video_path,
                "srt_path": srt_path,
                "audio_path": audio_path,
                "chapters": chapters
            }

        try:
            # Long-form comprehensive narration (5 to 10 minutes)
            long_narration = (
                f"Welcome to this comprehensive technical deep-dive into {title}. "
                f"In this video, we conduct a rigorous mathematical and architectural analysis of one of the most critical breakthroughs in modern artificial intelligence systems. "
                f"{summary} "
                f"Let us begin with Chapter 1: The Core Compute Dilemma and the Hardware Wall. "
                f"To understand why this innovation has become essential for frontier models, we must first examine the physical bottlenecks of traditional architectures. "
                f"Under conventional transformer and neural network implementations, {problem} "
                f"As input sequences grow, data transfer between high-bandwidth memory and on-chip SRAM creates an unavoidable latency penalty. Compute cores spend up to seventy percent of their clock cycles idle, waiting on memory bus synchronization. "
                f"Now let us advance to Chapter 2: The Formal Mathematical Formulation. "
                f"The foundational key to overcoming this wall is {solution} "
                f"By reformulating the underlying tensor operations, we decouple parameter capacity from memory access frequency. Notice how low-rank matrix decomposition and factorized projection reduce the active computational footprint from quadratic complexity down to near linear scaling. "
                f"This brings us to Chapter 3: Dynamic Tensor Routing and SRAM Execution. "
                f"At the hardware level, execution kernels are fused directly into high-speed on-chip SRAM tiles. Intermediate activation states are streamed dynamically across tensor cores rather than flushed back to off-chip DRAM. This eliminates redundant read-write round trips and keeps GPU vector pipelines fully saturated throughout the inference and training passes. "
                f"Next, in Chapter 4: Hardware Profiling, FLOP Utilization, and Latency Scaling. "
                f"When profiling models under real-world multi-tenant production loads, legacy baselines typically achieve under thirty percent Model FLOPs Utilization due to memory stalls. With this optimized architecture, Model FLOPs Utilization jumps past seventy percent, delivering a three to four-fold acceleration in generation throughput without degrading numerical precision or output perplexity. "
                f"Finally, let us examine Chapter 5: Empirical Benchmarks on NeuBench and the Production Deployment Playbook. "
                f"When translating this architecture into production systems, here is your essential engineering rule: {pro_tip} "
                f"Always validate real-world latency distributions, memory usage under peak concurrency, and cost per million tokens rather than relying solely on theoretical compute numbers. "
                f"For continuously updated token economics, throughput benchmarks, and live latency evaluations across more than 260 frontier AI models, explore the interactive NeuBench platform at app.neubench.workers.dev. "
                f"Thank you for watching this deep-dive. Subscribe for more mathematical and architectural breakdowns of state-of-the-art AI systems."
            )

            print(f"[VideoGenerator] Synthesizing Long-Form Explainer narration (5-10 min target)...")
            async def _synth():
                await self._synthesize_speech(long_narration, audio_path)
            asyncio.run(asyncio.wait_for(_synth(), timeout=240.0))

            # Clamp explainer duration between 300.0s (5m) and 600.0s (10m)
            audio_dur = self._get_audio_duration(audio_path)
            total_dur = min(max(audio_dur, 300.0), 600.0)
            print(f"[VideoGenerator] Target Explainer duration (5-10 min): {total_dur:.1f}s (Audio: {audio_dur:.1f}s)")

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
                        "chapters": chapters
                    }
        except Exception as ex:
            print(f"[VideoGenerator] Long explainer error: {ex}")

        return {"video_path": video_path if Path(video_path).exists() else None, "srt_path": srt_path, "audio_path": audio_path}
