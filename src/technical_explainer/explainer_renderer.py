"""
Technical Explainer Video Renderer.

Drives headless Chromium through the deterministic motion-graphics template and
streams high-quality frames straight into FFmpeg. Supports both 1080x1920 (9:16
shorts) and 1920x1080 (16:9 long-form).

Improvements over the old renderer:
- Premium SVG motion template with bundled Inter fonts
- Font-ready wait so the first frames are not rendered in a fallback face
- High-quality JPEG capture at the configured frame rate
- Subtle colour grade on encode
- Captions split from the actual narration for readable, in-sync subtitles
"""
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright

from .motion_template import generate_motion_html
from .motion_template_wide import generate_motion_html_wide

_WORD_RE = re.compile(r"[^.!?]+[.!?]?")


class ExplainerRenderer:
    def __init__(
        self,
        fps: int = 30,
        width: int = 1080,
        height: int = 1920,
        orientation: str = "portrait",
    ):
        self.fps = fps
        self.width = width
        self.height = height
        self.orientation = orientation

    # ------------------------------------------------------------ captions
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        seconds = max(0.0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _chunk_text(self, text: str, max_chars: int = 78) -> List[str]:
        """Split narration into readable caption lines."""
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return []
        sentences = [s.strip() for s in _WORD_RE.findall(text) if s.strip()]
        if not sentences:
            sentences = [text]

        chunks: List[str] = []
        for sentence in sentences:
            if len(sentence) <= max_chars:
                chunks.append(sentence)
                continue
            words = sentence.split()
            line = ""
            for w in words:
                if len(line) + len(w) + 1 > max_chars and line:
                    chunks.append(line)
                    line = w
                else:
                    line = f"{line} {w}".strip()
            if line:
                chunks.append(line)
        return chunks

    def _generate_srt(self, storyboard: Dict[str, Any], total_duration: float, srt_path: Path):
        scenes = storyboard.get("scenes", [])
        if not scenes:
            return
        blocks = []
        index = 1
        acc = 0.0
        for sc in scenes:
            fraction = sc.get("fraction", 1.0 / len(scenes))
            sc_dur = fraction * total_duration
            text = sc.get("narration_segment") or sc.get("caption") or sc.get("title") or ""
            chunks = self._chunk_text(text)
            if not chunks:
                chunks = [sc.get("title") or f"Scene {index}"]

            weights = [max(1, len(c)) for c in chunks]
            total_w = sum(weights) or 1
            t = acc
            for chunk, w in zip(chunks, weights):
                dur = sc_dur * (w / total_w)
                start = t
                end = t + dur
                blocks.append(
                    f"{index}\n{self._format_timestamp(start)} --> {self._format_timestamp(end)}\n{chunk}\n"
                )
                index += 1
                t = end
            acc += sc_dur

        srt_path.write_text("\n".join(blocks), encoding="utf-8")
        print(f"[ExplainerRenderer] Generated subtitles at {srt_path}", flush=True)

    # -------------------------------------------------------------- render
    def render(
        self,
        storyboard: Dict[str, Any],
        visemes: List[float],
        audio_path: Path,
        output_path: Path,
        work_dir: Path,
    ) -> Dict[str, Any]:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path = Path(audio_path)

        total_frames = len(visemes)
        if total_frames <= 0:
            raise RuntimeError("No frames to render (empty viseme track)")
        duration_sec = total_frames / self.fps
        print(
            f"[ExplainerRenderer] Rendering {total_frames} frames ({duration_sec:.1f}s) "
            f"@ {self.fps} fps -> {self.width}x{self.height}",
            flush=True,
        )

        # 1. Build the studio HTML + bundled fonts
        if self.orientation == "landscape":
            html_content = generate_motion_html_wide(
                storyboard, visemes, total_frames, fps=self.fps
            )
        else:
            html_content = generate_motion_html(storyboard, visemes, total_frames, fps=self.fps)
        html_file = work_dir / "explainer_studio.html"
        html_file.write_text(html_content, encoding="utf-8")

        fonts_src = Path(__file__).parent / "fonts"
        fonts_dst = work_dir / "fonts"
        if fonts_src.exists():
            fonts_dst.mkdir(parents=True, exist_ok=True)
            for item in fonts_src.iterdir():
                if item.is_file():
                    shutil.copy(item, fonts_dst / item.name)

        # 2. Subtitles
        srt_path = output_path.with_suffix(".srt")
        self._generate_srt(storyboard, duration_sec, srt_path)

        # 3. FFmpeg encoder (frames arrive as high-quality JPEG on stdin)
        vf = "eq=contrast=1.04:saturation=1.06:brightness=-0.005"
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-r", str(self.fps),
            "-i", "-",
            "-i", str(audio_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        print(f"[ExplainerRenderer] Spawning FFmpeg video pipe: {output_path.name}", flush=True)
        ffmpeg_log_path = work_dir / "ffmpeg_render.log"
        ffmpeg_log_file = open(ffmpeg_log_path, "w", encoding="utf-8")
        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=ffmpeg_log_file,
        )

        t_start = time.time()

        # 4. Render deterministically frame by frame
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-gpu-sandbox",
                    "--disable-dev-shm-usage",
                    "--force-color-profile=srgb",
                    "--font-render-hinting=none",
                ],
            )
            page = browser.new_page(
                viewport={"width": self.width, "height": self.height},
                device_scale_factor=1,
            )
            page.goto(html_file.resolve().as_uri(), wait_until="load")

            # Critical: wait for the bundled fonts so frame 0 is not a fallback face
            try:
                page.evaluate("async () => { await document.fonts.ready; return true; }")
            except Exception:
                pass
            page.wait_for_timeout(150)

            page.evaluate("window.renderFrame(0, 0.0)")

            for frame_idx in range(total_frames):
                current_time = frame_idx / self.fps
                page.evaluate(f"window.renderFrame({frame_idx}, {current_time:.4f})")
                frame_bytes = page.screenshot(type="jpeg", quality=90)

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
                    print(
                        f"[ExplainerRenderer] Rendered {frame_idx + 1}/{total_frames} "
                        f"frames ({pct:.1f}%) [{render_fps:.1f} FPS]",
                        flush=True,
                    )

            browser.close()

        # 5. Finalize
        ffmpeg_proc.stdin.close()
        ret = ffmpeg_proc.wait()
        ffmpeg_log_file.close()

        if ret != 0:
            err_msg = ffmpeg_log_path.read_text(encoding="utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg encoding failed (code {ret}): {err_msg}")

        total_time = time.time() - t_start
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(
            f"[ExplainerRenderer] Finished in {total_time:.1f}s ({file_size_mb:.2f} MB) -> {output_path}",
            flush=True,
        )

        return {
            "video_path": str(output_path),
            "srt_path": str(srt_path),
            "audio_path": str(audio_path),
            "duration": duration_sec,
            "fps": self.fps,
            "frames": total_frames,
            "file_size_mb": round(file_size_mb, 2),
        }
