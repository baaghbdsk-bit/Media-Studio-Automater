"""
Headless Playwright WebGL Video Renderer.
Drives the Three.js 3D Presenter Studio application frame-by-frame and pipes
captured frames directly into FFmpeg to produce crisp 1080x1920 9:16 vertical MP4s.
Zero dropped frames, deterministic audio-sync, and zero intermediate disk image files.
"""
import os
import sys
import json
import shutil
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright

from .studio_template import generate_studio_html


class PresenterRenderer:
    def __init__(self, fps: int = 24):
        self.fps = fps

    def _generate_srt(self, storyboard: Dict[str, Any], total_duration: float, srt_path: Path):
        """Generates synchronized SubRip (.srt) caption file from storyboard scenes."""
        scenes = storyboard.get("scenes", [])
        if not scenes:
            return

        srt_blocks = []
        acc_time = 0.0

        for i, sc in enumerate(scenes, 1):
            fraction = sc.get("fraction", 1.0 / len(scenes))
            sc_dur = fraction * total_duration
            start_sec = acc_time
            end_sec = acc_time + sc_dur
            acc_time += sc_dur

            start_str = self._format_timestamp(start_sec)
            end_str = self._format_timestamp(end_sec)
            caption = sc.get("caption") or sc.get("act_title") or f"Act {i}"

            srt_blocks.append(f"{i}\n{start_str} --> {end_str}\n{caption}\n")

        srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
        print(f"[PresenterRenderer] Generated subtitles at {srt_path}")

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def render(
        self,
        storyboard: Dict[str, Any],
        visemes: List[float],
        audio_path: Path,
        output_path: Path,
        work_dir: Path
    ) -> Dict[str, Any]:
        """
        Renders the complete 3D presenter video deterministically.
        Pipes raw frames directly into FFmpeg to eliminate disk thrashing.
        """
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path = Path(audio_path)

        total_frames = len(visemes)
        duration_sec = total_frames / self.fps
        print(f"[PresenterRenderer] Starting 3D WebGL render: {total_frames} frames ({duration_sec:.1f}s) @ {self.fps} fps")

        # 1. Generate Studio HTML
        html_content = generate_studio_html(storyboard, visemes, total_frames, fps=self.fps)
        html_file = work_dir / "studio.html"
        html_file.write_text(html_content, encoding="utf-8")

        # 2. Copy offline Three.js bundle
        three_js_src = Path(__file__).parent / "three.min.js"
        shutil.copy(three_js_src, work_dir / "three.min.js")

        # 3. Generate SRT subtitle file
        srt_path = output_path.with_suffix(".srt")
        self._generate_srt(storyboard, duration_sec, srt_path)

        # 4. Prepare FFmpeg child process with image2pipe stdin
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-r", str(self.fps),
            "-i", "-",
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ]

        print(f"[PresenterRenderer] Spawning FFmpeg video pipe: {output_path.name}", flush=True)
        ffmpeg_log_path = work_dir / "ffmpeg_render.log"
        ffmpeg_log_file = open(ffmpeg_log_path, "w", encoding="utf-8")

        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=ffmpeg_log_file
        )

        t_start = time.time()

        # 5. Launch Playwright Chromium with WebGL
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--enable-webgl",
                    "--use-gl=angle",
                    "--use-angle=gl",
                    "--no-sandbox",
                    "--disable-gpu-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.goto(html_file.resolve().as_uri(), wait_until="load")

            # Warmup render
            page.evaluate("window.renderFrame(0, 0.0)")

            # Render loop: deterministic frame stepping
            for frame_idx in range(total_frames):
                current_time = frame_idx / self.fps
                page.evaluate(f"window.renderFrame({frame_idx}, {current_time:.4f})")
                frame_bytes = page.screenshot(type="jpeg", quality=85)
                
                try:
                    ffmpeg_proc.stdin.write(frame_bytes)
                except BrokenPipeError:
                    ffmpeg_log_file.close()
                    err = ffmpeg_log_path.read_text(encoding="utf-8", errors="ignore")
                    raise RuntimeError(f"FFmpeg stdin pipe broke: {err}")

                if frame_idx % 60 == 0 or frame_idx == total_frames - 1:
                    pct = (frame_idx + 1) / total_frames * 100.0
                    elapsed = time.time() - t_start
                    render_fps = (frame_idx + 1) / elapsed if elapsed > 0 else 0
                    print(f"[PresenterRenderer] Rendered {frame_idx + 1}/{total_frames} frames ({pct:.1f}%) [{render_fps:.1f} FPS]", flush=True)

            browser.close()

        # 6. Finalize FFmpeg
        ffmpeg_proc.stdin.close()
        ret = ffmpeg_proc.wait()
        ffmpeg_log_file.close()

        if ret != 0:
            err_msg = ffmpeg_log_path.read_text(encoding="utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg encoding failed (code {ret}): {err_msg}")

        total_time = time.time() - t_start
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"[PresenterRenderer] Finished! Video rendered in {total_time:.1f}s ({file_size_mb:.2f} MB) -> {output_path}", flush=True)

        return {
            "video_path": str(output_path),
            "srt_path": str(srt_path),
            "audio_path": str(audio_path),
            "duration": duration_sec,
            "fps": self.fps,
            "frames": total_frames,
            "file_size_mb": round(file_size_mb, 2)
        }
