import sys
import os
import asyncio
import subprocess
import json
import re
import shutil
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


class VideoGenerator:
    """
    Cinematic Video Generation Engine for Media Studio Automater.
    Replaces legacy slow Manim/Canvas pipelines with high-speed, GPU-accelerated HyperFrames + Edge-TTS + GSAP + FFmpeg:
    - 9:16 Vertical (1080x1920) for YouTube Shorts, Instagram Reels, Pinterest Video Pins
    - 16:9 Landscape (1920x1080) for YouTube Long-Form Documentaries & Explainers
    - Microsoft Neural TTS Voiceover (en-US-ChristopherNeural / en-US-AndrewMultilingualNeural)
    - Broadcast vocal mastering chain (Highpass, warmth, presence, optical compression)
    - Full multi-track cinematic sound design (sub-booms, risers, mechanical locks) and ambient score
    - Synchronized Subtitles (.srt) and chapter markers
    """

    DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"
    FALLBACK_VOICES = ("en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-AriaNeural")
    DEFAULT_RATE = "+6%"
    TTS_MAX_ATTEMPTS = 4
    TTS_MIN_AUDIO_BYTES = 1024

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.output_dir = self.base_dir / "generated_visuals" / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Locate ffmpeg / ffprobe
        self.ffmpeg_bin = shutil.which("ffmpeg") or r"C:\Users\vivek\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
        self.ffprobe_bin = shutil.which("ffprobe") or r"C:\Users\vivek\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
        
        # Locate local HyperFrames binary (cross-platform Windows & Linux)
        local_hf_cmd = self.base_dir / "node_modules" / ".bin" / "hyperframes.cmd"
        local_hf_sh = self.base_dir / "node_modules" / ".bin" / "hyperframes"
        global_hf = shutil.which("hyperframes")
        fallback_hf = Path(r"E:\Projects\yt auto\ai-explainer-studio\node_modules\.bin\hyperframes.cmd")

        if local_hf_cmd.exists():
            self.hyperframes_cmd = [str(local_hf_cmd)]
        elif local_hf_sh.exists():
            self.hyperframes_cmd = [str(local_hf_sh)]
        elif global_hf:
            self.hyperframes_cmd = [global_hf]
        elif fallback_hf.exists():
            self.hyperframes_cmd = [str(fallback_hf)]
        else:
            npx_bin = shutil.which("npx") or "npx"
            self.hyperframes_cmd = [npx_bin, "hyperframes"]
        self.hyperframes_bin = self.hyperframes_cmd[0]

    def _get_audio_duration(self, audio_path: str) -> float:
        """Determines duration in seconds of the synthesized audio file."""
        try:
            res = subprocess.run(
                [self.ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return float(data.get("format", {}).get("duration", 60.0))
        except Exception:
            pass
        return 60.0

    def _generate_srt_file(self, scenes: List[Dict[str, Any]], srt_path: str):
        """Builds standard SubRip (.srt) subtitle track."""
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

    def _synthesize_voice_and_audio_suite(self, text: str, output_master_wav: str, duration_target: float) -> float:
        """
        Synthesizes Microsoft Neural voiceover, applies broadcast mastering chain,
        generates cinematic sub-booms & Foley, mixes in an ambient synth score bed,
        and masters the final track.
        """
        work_dir = Path(output_master_wav).parent
        raw_mp3 = str(work_dir / "voice_raw.mp3")
        proc_wav = str(work_dir / "voice_proc.wav")
        score_wav = str(work_dir / "ambient_score.wav")

        # 1. Synthesize voice with Edge-TTS.
        # GitHub-hosted runners have intermittently received NoAudioReceived from
        # Microsoft's free Edge TTS endpoint. Retry across voices and validate the
        # audio before handing it to ffmpeg, so one dead response cannot abort the
        # whole scheduled broadcast. EDGE_TTS_PROXY can be set in CI when the
        # runner's egress IP is throttled/blocked by the TTS service.
        proxy = (os.environ.get("EDGE_TTS_PROXY") or "").strip() or None

        async def _synth_once(voice: str):
            tts = edge_tts.Communicate(
                text,
                voice,
                rate=self.DEFAULT_RATE,
                proxy=proxy,
            )
            await tts.save(raw_mp3)

        async def _synth():
            voices = [self.DEFAULT_VOICE] + [
                v for v in self.FALLBACK_VOICES if v != self.DEFAULT_VOICE
            ]
            errors = []
            for attempt in range(1, self.TTS_MAX_ATTEMPTS + 1):
                voice = voices[(attempt - 1) % len(voices)]
                try:
                    Path(raw_mp3).unlink(missing_ok=True)
                except OSError:
                    pass
                try:
                    await asyncio.wait_for(_synth_once(voice), timeout=90.0)
                    size = Path(raw_mp3).stat().st_size if Path(raw_mp3).exists() else 0
                    if size >= self.TTS_MIN_AUDIO_BYTES:
                        if attempt > 1:
                            print(f"[VideoGenerator] Voiceover recovered with {voice} after {attempt} attempts.")
                        return
                    errors.append(f"{voice}: empty/short audio ({size} bytes)")
                except Exception as exc:
                    errors.append(f"{voice}: {exc}")
                print(
                    f"[VideoGenerator] TTS attempt {attempt}/{self.TTS_MAX_ATTEMPTS} failed "
                    f"({errors[-1]}); trying next voice..."
                )
            raise RuntimeError("Edge TTS failed after retries: " + " | ".join(errors))

        asyncio.run(_synth())

        return self._master_audio_from_mp3(raw_mp3, output_master_wav, duration_target)

    def _master_audio_from_mp3(self, raw_mp3: str, output_master_wav: str,
                               duration_target: float) -> float:
        """Process an existing voice MP3 into a mastered, broadcast-ready WAV."""
        work_dir = Path(output_master_wav).parent
        proc_wav = str(work_dir / "voice_proc.wav")
        score_wav = str(work_dir / "ambient_score.wav")

        # Broadcast vocal chain: rumble cut, warmth, presence, gentle levelling.
        vocal_filter = (
            "highpass=f=75,"
            "equalizer=f=180:t=q:w=1.2:g=1.8,"
            "equalizer=f=3500:t=q:w=1.0:g=2.5,"
            "equalizer=f=11000:t=q:w=0.8:g=1.5,"
            "compand=attacks=0.01:decays=0.08:points=-80/-80|-45/-32|-20/-13|-8/-6|0/-1.2:soft-knee=6"
        )
        subprocess.run([self.ffmpeg_bin, "-y", "-i", raw_mp3, "-af", vocal_filter, proc_wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        measured_dur = self._get_audio_duration(proc_wav)
        total_dur = max(measured_dur + 2.0, duration_target)
        fade_out_start = max(0.0, total_dur - 3.0)

        # Low ambient bed, ducked under the voice by the mix below.
        subprocess.run([
            self.ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", f"sine=frequency=55:duration={total_dur}",
            "-f", "lavfi", "-i", f"sine=frequency=110:duration={total_dur}",
            "-f", "lavfi", "-i", f"anoisesrc=d={total_dur}:c=pink:r=48000:a=0.025",
            "-filter_complex",
            "[0]volume=0.32[sub];"
            "[1]volume=0.18,chorus=0.6:0.8:60:0.4:0.25:2[pad];"
            "[2]lowpass=f=350,volume=0.2[tape];"
            f"[sub][pad][tape]amix=inputs=3:normalize=0,volume=0.35,afade=t=in:st=0:d=2.0,afade=t=out:st={fade_out_start:.1f}:d=3[score_raw]",
            "-map", "[score_raw]", "-t", f"{total_dur:.2f}", score_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Short-form loudness target: -14 LUFS, true peak <= -1.5 dBTP.
        master_filter = (
            "[0]volume=1.0[voc];"
            "[1]volume=0.10[bed];"
            "[voc][bed]amix=inputs=2:normalize=0,"
            "loudnorm=I=-14:TP=-1.5:LRA=11,"
            "alimiter=limit=-1.0dB:attack=5:release=50[master]"
        )
        subprocess.run([
            self.ffmpeg_bin, "-y",
            "-i", proc_wav,
            "-i", score_wav,
            "-filter_complex", master_filter,
            "-map", "[master]",
            "-t", f"{total_dur:.2f}",
            output_master_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        return total_dur

    def _render_hyperframes(self, comp_dir: Path, output_mp4: str) -> bool:
        """Render with HyperFrames, then normalise audio loudness.

        Visible motion is authored in the composition itself (bounded
        parallax/loop layers), so no grain or video re-encode is needed. The
        loudness pass only re-encodes audio, keeping file size and picture
        quality intact.
        """
        output = Path(output_mp4)
        raw_output = output.with_name(output.stem + "_raw.mp4")
        cmd = self.hyperframes_cmd + [
            "render",
            str(comp_dir),
            "-o", str(raw_output),
            "-q", "standard"
        ]
        print(f"[VideoGenerator] 🎬 HyperFrames rendering composition: {comp_dir.name}...")
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900)
            if proc.returncode != 0 or not raw_output.exists() or raw_output.stat().st_size <= 50000:
                print(f"[VideoGenerator] Render note: {proc.stderr[-400:] if proc.stderr else proc.stdout[-400:]}")
                return False

            subprocess.run([
                self.ffmpeg_bin, "-y", "-v", "error",
                "-i", str(raw_output),
                "-c:v", "copy",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart",
                str(output),
            ], check=True, capture_output=True)
            raw_output.unlink(missing_ok=True)
            print(f"[VideoGenerator] ✅ Cinematic video ready: {output.name} ({round(output.stat().st_size / (1024*1024), 2)} MB)")
            return True
        except Exception as ex:
            print(f"[VideoGenerator] HyperFrames execution note: {ex}")
            return False

    def _compose_beginner_friendly_story(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build on-screen story cards and a grounded, filler-free narration."""
        from src.content_quality import clean_text, trim_to_sentences

        source = topic_data or {}
        title = str(source.get("title") or "Modern Computing Breakthrough").strip()

        real_hook = str(source.get("hook") or "").strip()
        real_analogy = str(source.get("analogy") or "").strip()
        real_problem = str(source.get("problem") or "").strip()
        real_solution = str(source.get("solution") or "").strip()
        real_takeaway = str(source.get("takeaway") or "").strip()
        real_pro_tip = str(source.get("pro_tip") or "").strip()
        summary = str(source.get("summary") or "").strip()

        # On-screen fallbacks stay visual only. They are never narrated, so a
        # missing field cannot inject canned "magic glasses" prose into the VO.
        hook = real_hook or f"Have you ever wondered how {title} actually works?"
        analogy = real_analogy or "Think of it like sorting a pile of letters by hand: slow, easy to get wrong, and impossible to scale."
        problem = real_problem or "The old approach was slow and broke down as the input grew."
        solution = real_solution or f"{title} changes that by handling the whole problem in one pass."
        takeaway = real_takeaway or title
        pro_tip = real_pro_tip or "Look for the concrete constraint this removes, not the buzzword."

        is_news = str(source.get("pillar") or "").upper() == "NEWS"
        if is_news:
            # Grounded news: only the headline and the sourced summary.
            narration_parts = [real_hook, summary]
        else:
            narration_parts = [
                real_hook, real_analogy, real_problem,
                real_solution, real_takeaway, real_pro_tip,
            ]

        narration = clean_text(" ".join(p for p in narration_parts if p))
        if not narration:
            narration = clean_text(summary or f"{title}. Here is what changed and why it matters.")
        narration = trim_to_sentences(narration, 105 if is_news else 115)

        return {
            "title": title,
            "hook": hook,
            "analogy": analogy,
            "summary": summary,
            "problem": problem,
            "solution": solution,
            "takeaway": takeaway,
            "pro_tip": pro_tip,
            "narration": narration,
        }

    def generate_dynamic_short(self, topic_data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Optional[str]]:
        """Render a 9:16 Short with spoken script, AI storyboard and object animation."""
        from src.short_script import build_short_script
        from src.short_script_ai import build_short_script_ai
        from src.storyboard_ai import build_storyboard_ai, deterministic_storyboard
        from src.voice import synthesize_performance, write_srt
        from src.short_visual_v3 import build_short_html_v3
        from scripts.qa_video import check_video

        script = build_short_script_ai(topic_data) or build_short_script(topic_data)
        storyboard = build_storyboard_ai(topic_data, script) or deterministic_storyboard(topic_data, script)
        title = str(script.get("title") or topic_data.get("title") or "AI Explained")
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')[:35]
        work_dir = self.output_dir / f"short_{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)

        video_path = str(work_dir / f"cinematic_short_{slug}.mp4")
        audio_path = str(work_dir / "narration_master.wav")
        srt_path = str(work_dir / f"subtitles_{slug}.srt")

        if dry_run:
            if not Path(video_path).exists():
                Path(video_path).touch()
            return {"video_path": video_path, "srt_path": srt_path, "audio_path": audio_path}

        try:
            raw_mp3 = work_dir / "voice_raw.mp3"
            voice_result = None
            for voice in ("en-US-AvaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural"):
                try:
                    voice_result = synthesize_performance(
                        script["narration"], str(raw_mp3), voice=voice
                    )
                    break
                except RuntimeError as exc:
                    print(f"[VideoGenerator] Voice {voice} failed: {exc}")
            if voice_result is None:
                raise RuntimeError("All narration voices failed")

            words = voice_result["words"]
            target = max(40.0, (words[-1]["end"] if words else 0.0) + 2.0)
            total_dur = self._master_audio_from_mp3(str(raw_mp3), audio_path, target)
            write_srt(words, srt_path)

            html = build_short_html_v3(topic_data, script, storyboard, words, total_dur)
            (work_dir / "index.html").write_text(html, encoding="utf-8")
            (work_dir / "script.txt").write_text(script["narration"], encoding="utf-8")

            if self._render_hyperframes(work_dir, video_path):
                qa_ok, qa_report = check_video(video_path)
                print(f"[VideoGenerator] QA: {qa_report}")
                if not qa_ok:
                    print(f"[VideoGenerator] QA failed: {qa_report.get('errors')}")
                    return {"video_path": None, "srt_path": srt_path, "audio_path": audio_path}
                return {"video_path": video_path, "srt_path": srt_path, "audio_path": audio_path}
        except Exception as ex:
            print(f"[VideoGenerator] Short generation error: {ex}")

        return {
            "video_path": video_path if Path(video_path).exists() else None,
            "srt_path": srt_path,
            "audio_path": audio_path
        }

    def generate_dynamic_explainer(self, topic_data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Optional[str]]:
        """
        Renders a full 16:9 Landscape (1920x1080) Documentary Explainer Video.
        Follows the Beginner-Friendly AMM Framework with 5 Chapters.
        """
        story = self._compose_beginner_friendly_story(topic_data)
        title = story["title"]
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower()).strip('_')[:35]
        work_dir = self.output_dir / f"explainer_{slug}"
        work_dir.mkdir(parents=True, exist_ok=True)

        video_path = str(work_dir / f"youtube_explainer_{slug}.mp4")
        audio_path = str(work_dir / "narration_master.wav")
        srt_path = str(work_dir / f"explainer_subtitles_{slug}.srt")

        chapters = [
            "00:00 Chapter 01: The Curious Hook & Dilemma",
            "00:12 Chapter 02: The Real-World Metaphor",
            "00:24 Chapter 03: The Hidden Bottleneck",
            "00:36 Chapter 04: The Architectural Unlock",
            "00:48 Chapter 05: Core Takeaways & Benchmarks"
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

        narration_text = story["narration"]

        try:
            print(f"[VideoGenerator] 🎙️ Synthesizing Long-Form Explainer audio for '{title[:35]}'...")
            total_dur = self._synthesize_voice_and_audio_suite(narration_text, audio_path, duration_target=60.0)

            # Build 16:9 Widescreen HyperFrames Composition (5 Chapters)
            comp_html = self._build_widescreen_explainer_html(
                title=story["title"],
                hook=story["hook"],
                analogy=story["analogy"],
                problem=story["problem"],
                solution=story["solution"],
                takeaway=story["takeaway"],
                pro_tip=story["pro_tip"],
                duration=total_dur
            )
            index_path = work_dir / "index.html"
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(comp_html)

            # Render with HyperFrames
            ok = self._render_hyperframes(work_dir, video_path)
            if ok:
                return {
                    "video_path": video_path,
                    "srt_path": srt_path,
                    "audio_path": audio_path,
                    "chapters": chapters
                }
        except Exception as ex:
            print(f"[VideoGenerator] Explainer error: {ex}")

        return {
            "video_path": video_path if Path(video_path).exists() else None,
            "srt_path": srt_path,
            "audio_path": audio_path,
            "chapters": chapters
        }

    def _build_vertical_short_html(self, title: str, hook: str, analogy: str, problem: str, solution: str, takeaway: str, pro_tip: str, duration: float, mode: str = "concept") -> str:
        """Generates full 9:16 Vertical (1080x1920) HyperFrames composition with 5 beginner-friendly scenes."""
        act_dur = duration / 5.0
        if mode == "news":
            badge_1, badge_2, badge_3, badge_4, badge_5 = "BREAKING", "WHAT HAPPENED", "WHY IT MATTERS", "THE REACTION", "WHAT'S NEXT"
            head_2, head_3, head_4, head_5 = "The <span>Story</span>", "The <span>Stakes</span>", "The <span>Fallout</span>", "The <span>Bottom Line</span>"
            card_1, card_2, card_3, card_4, card_5 = "The Headline", "The Details", "The Risk", "The Response", "Why It Matters"
        else:
            badge_1, badge_2, badge_3, badge_4, badge_5 = "THE BIG QUESTION", "REAL-WORLD METAPHOR", "THE HIDDEN PROBLEM", "THE BREAKTHROUGH", "KEY TAKEAWAY"
            head_2, head_3, head_4, head_5 = "Think Of It <span>Like This</span>", "Why Naive Systems <span>Fail</span>", "How It <span>Actually Works</span>", "What To <span>Remember</span>"
            card_1, card_2, card_3, card_4, card_5 = "Ever Wondered?", "The Intuition", "The Bottleneck", "The Mechanism", "The Big Idea"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title} • Vertical Short</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      margin: 0; padding: 0; background: #020409; color: #f8fafc;
      font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif; overflow: hidden;
    }}
    #root {{
      width: 1080px; height: 1920px; position: relative; overflow: hidden; background: #020409;
    }}
    .bg-canvas {{
      position: absolute; inset: 0; z-index: 0;
      background: radial-gradient(circle at 50% 30%, #0d1b33 0%, #040813 70%, #010308 100%);
    }}
    .bg-canvas::before {{
      content: ""; position: absolute; inset: 0;
      background-image: 
        radial-gradient(1.5px 1.5px at 20% 30%, rgba(56, 189, 248, 0.5) 1.5px, transparent 0),
        radial-gradient(1.5px 1.5px at 80% 70%, rgba(192, 132, 252, 0.45) 1.5px, transparent 0);
      background-size: 320px 320px; opacity: 0.6;
    }}
    .scene {{
      position: absolute; inset: 0; opacity: 0; pointer-events: none;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 100px 60px; z-index: 2; text-align: center;
    }}
    .badge {{
      display: inline-flex; align-items: center; gap: 10px;
      padding: 12px 28px; border-radius: 999px;
      background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.4);
      color: #38bdf8; font-size: 20px; font-weight: 700; letter-spacing: 0.14em;
      text-transform: uppercase; margin-bottom: 30px;
    }}
    .hero-title {{
      font-size: 58px; font-weight: 900; line-height: 1.15; margin-bottom: 24px;
      background: linear-gradient(135deg, #ffffff 40%, #cbd5e1 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .hero-title span {{
      background: linear-gradient(135deg, #38bdf8, #c084fc);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .card {{
      width: 100%; max-width: 920px; padding: 44px 40px; border-radius: 28px;
      background: rgba(9, 14, 26, 0.88); border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 30px 80px rgba(0,0,0,0.7); text-align: left; margin-top: 24px;
    }}
    .card-title {{ font-size: 28px; font-weight: 800; color: #38bdf8; margin-bottom: 16px; }}
    .card-body {{ font-size: 24px; color: #cbd5e1; line-height: 1.55; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.1f}" data-width="1080" data-height="1920">
    <audio id="narration" src="narration_master.wav" data-start="0" data-duration="{duration:.1f}" data-volume="1"></audio>
    <div class="bg-canvas clip" data-start="0" data-duration="{duration:.1f}"></div>

    <!-- Act 1: The Curious Hook -->
    <div id="scene1" class="scene clip" data-start="0" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="badge"><span style="width:8px; height:8px; border-radius:50%; background:#38bdf8;"></span> {badge_1}</div>
      <h1 class="hero-title">{title}</h1>
      <div class="card">
        <div class="card-title">{card_1}</div>
        <div class="card-body">{hook}</div>
      </div>
    </div>

    <!-- Act 2: Everyday Metaphor -->
    <div id="scene2" class="scene clip" data-start="{act_dur:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="badge" style="border-color:#38bdf8; color:#38bdf8;">{badge_2}</div>
      <h2 class="hero-title">{head_2}</h2>
      <div class="card" style="border-color: rgba(56, 189, 248, 0.4);">
        <div class="card-title" style="color:#38bdf8;">{card_2}</div>
        <div class="card-body">{analogy}</div>
      </div>
    </div>

    <!-- Act 3: Detailed Bottleneck -->
    <div id="scene3" class="scene clip" data-start="{act_dur*2:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="badge" style="border-color:#f43f5e; color:#f43f5e;">{badge_3}</div>
      <h2 class="hero-title">{head_3}</h2>
      <div class="card" style="border-color: rgba(244, 63, 94, 0.4);">
        <div class="card-title" style="color:#f43f5e;">{card_3}</div>
        <div class="card-body">{problem}</div>
      </div>
    </div>

    <!-- Act 4: The Technical Unlock -->
    <div id="scene4" class="scene clip" data-start="{act_dur*3:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="badge" style="border-color:#c084fc; color:#c084fc;">{badge_4}</div>
      <h2 class="hero-title">{head_4}</h2>
      <div class="card" style="border-color: rgba(192, 132, 252, 0.4);">
        <div class="card-title" style="color:#c084fc;">{card_4}</div>
        <div class="card-body">{solution}</div>
      </div>
    </div>

    <!-- Act 5: The 'Aha!' Takeaway -->
    <div id="scene5" class="scene clip" data-start="{act_dur*4:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="badge" style="border-color:#34d399; color:#34d399;">{badge_5}</div>
      <h2 class="hero-title">{head_5}</h2>
      <div class="card" style="border-color: rgba(52, 211, 153, 0.4);">
        <div class="card-title" style="color:#34d399;">{card_5}</div>
        <div class="card-body">{takeaway}<br><br><span style="color:#38bdf8; font-weight:700;">💡 Rule:</span> {pro_tip}</div>
      </div>
    </div>
  </div>

  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    const d = {act_dur:.2f};
    tl.to("#scene1", {{ opacity: 1, duration: 0.5 }}, 0);
    tl.to("#scene1", {{ opacity: 0, duration: 0.5 }}, d - 0.5);
    tl.fromTo("#scene2", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d);
    tl.to("#scene2", {{ opacity: 0, duration: 0.5 }}, (d * 2) - 0.5);
    tl.fromTo("#scene3", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d * 2);
    tl.to("#scene3", {{ opacity: 0, duration: 0.5 }}, (d * 3) - 0.5);
    tl.fromTo("#scene4", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d * 3);
    tl.to("#scene4", {{ opacity: 0, duration: 0.5 }}, (d * 4) - 0.5);
    tl.fromTo("#scene5", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d * 4);
    tl.to("#scene5", {{ opacity: 0, duration: 0.5 }}, {duration:.1f} - 0.5);
    window.__timelines["main"] = tl;
  </script>
</body>
</html>"""

    def _build_widescreen_explainer_html(self, title: str, hook: str, analogy: str, problem: str, solution: str, takeaway: str, pro_tip: str, duration: float) -> str:
        """Generates full 16:9 Landscape (1920x1080) HyperFrames composition with 5 beginner-friendly chapters."""
        act_dur = duration / 5.0
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title} • Technical Explainer</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      margin: 0; padding: 0; background: #020409; color: #f8fafc;
      font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif; overflow: hidden;
    }}
    #root {{
      width: 1920px; height: 1080px; position: relative; overflow: hidden; background: #020409;
    }}
    .bg-canvas {{
      position: absolute; inset: 0; z-index: 0;
      background: radial-gradient(circle at 50% 35%, #0d1b33 0%, #050a17 65%, #010308 100%);
    }}
    .bg-canvas::before {{
      content: ""; position: absolute; inset: 0;
      background-image: 
        radial-gradient(1px 1px at 15% 25%, rgba(255, 255, 255, 0.4) 1px, transparent 0),
        radial-gradient(1.5px 1.5px at 75% 65%, rgba(56, 189, 248, 0.45) 1.5px, transparent 0);
      background-size: 480px 480px; opacity: 0.65;
    }}
    .scene {{
      position: absolute; inset: 0; opacity: 0; pointer-events: none;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 60px 100px; z-index: 2; text-align: center;
    }}
    .chapter-pill {{
      display: inline-flex; align-items: center; gap: 10px;
      padding: 8px 22px; border-radius: 999px;
      background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.35);
      color: #38bdf8; font-size: 15px; font-weight: 700; letter-spacing: 0.14em;
      text-transform: uppercase; margin-bottom: 20px;
    }}
    .hero-title {{
      font-size: 64px; font-weight: 900; letter-spacing: -0.03em; line-height: 1.12; margin-bottom: 20px;
      background: linear-gradient(135deg, #ffffff 40%, #e2e8f0 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .hero-title span {{
      background: linear-gradient(135deg, #38bdf8, #c084fc);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .stage-card {{
      width: 100%; max-width: 1300px; padding: 40px 48px; border-radius: 24px;
      background: rgba(9, 14, 26, 0.88); border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7); text-align: left;
    }}
    .stage-card-title {{
      font-size: 20px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;
    }}
    .stage-card-body {{
      font-size: 25px; color: #cbd5e1; line-height: 1.55;
    }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.1f}" data-width="1920" data-height="1080">
    <audio id="narration" src="narration_master.wav" data-start="0" data-duration="{duration:.1f}" data-volume="1"></audio>
    <div class="bg-canvas clip" data-start="0" data-duration="{duration:.1f}"></div>

    <!-- Chapter 1: The Curious Hook -->
    <div id="scene1" class="scene clip" data-start="0" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="chapter-pill">CHAPTER 01 &bull; THE BIG QUESTION</div>
      <h1 class="hero-title">{title}</h1>
      <div class="stage-card">
        <div class="stage-card-title" style="color:#38bdf8;">Curious Dilemma</div>
        <div class="stage-card-body">{hook}</div>
      </div>
    </div>

    <!-- Chapter 2: Real-World Metaphor -->
    <div id="scene2" class="scene clip" data-start="{act_dur:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="chapter-pill" style="border-color:#38bdf8; color:#38bdf8;">CHAPTER 02 &bull; THE EVERYDAY METAPHOR</div>
      <h2 class="hero-title">Think Of It <span>Like This</span></h2>
      <div class="stage-card" style="border-color: rgba(56, 189, 248, 0.4);">
        <div class="stage-card-title" style="color:#38bdf8;">Intuitive Analogy</div>
        <div class="stage-card-body">{analogy}</div>
      </div>
    </div>

    <!-- Chapter 3: The Bottleneck -->
    <div id="scene3" class="scene clip" data-start="{act_dur*2:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="chapter-pill" style="border-color:#f43f5e; color:#f43f5e;">CHAPTER 03 &bull; THE DETAILED PROBLEM</div>
      <h2 class="hero-title">Why Traditional Systems <span>Stall</span></h2>
      <div class="stage-card" style="border-color: rgba(244, 63, 94, 0.4);">
        <div class="stage-card-title" style="color:#f43f5e;">The Bottleneck</div>
        <div class="stage-card-body">{problem}</div>
      </div>
    </div>

    <!-- Chapter 4: The Unlock -->
    <div id="scene4" class="scene clip" data-start="{act_dur*3:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="chapter-pill" style="border-color:#c084fc; color:#c084fc;">CHAPTER 04 &bull; THE ARCHITECTURAL UNLOCK</div>
      <h2 class="hero-title">How It <span>Actually Works</span></h2>
      <div class="stage-card" style="border-color: rgba(192, 132, 252, 0.4);">
        <div class="stage-card-title" style="color:#c084fc;">The Mechanism</div>
        <div class="stage-card-body">{solution}</div>
      </div>
    </div>

    <!-- Chapter 5: Takeaway -->
    <div id="scene5" class="scene clip" data-start="{act_dur*4:.1f}" data-duration="{act_dur:.1f}" data-track-index="0">
      <div class="chapter-pill" style="border-color:#34d399; color:#34d399;">CHAPTER 05 &bull; PRODUCTION STANDARDS</div>
      <h2 class="hero-title">Key <span>Takeaways & Benchmarks</span></h2>
      <div class="stage-card" style="border-color: rgba(52, 211, 153, 0.4);">
        <div class="stage-card-title" style="color:#34d399;">Production Takeaway</div>
        <div class="stage-card-body">{takeaway}<br><br><span style="color:#38bdf8; font-weight:700;">💡 Engineering Standard:</span> {pro_tip}</div>
      </div>
    </div>
  </div>

  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    const d = {act_dur:.2f};
    tl.to("#scene1", {{ opacity: 1, duration: 0.5 }}, 0);
    tl.to("#scene1", {{ opacity: 0, duration: 0.5 }}, d - 0.5);
    tl.fromTo("#scene2", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d);
    tl.to("#scene2", {{ opacity: 0, duration: 0.5 }}, (d * 2) - 0.5);
    tl.fromTo("#scene3", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d * 2);
    tl.to("#scene3", {{ opacity: 0, duration: 0.5 }}, (d * 3) - 0.5);
    tl.fromTo("#scene4", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d * 3);
    tl.to("#scene4", {{ opacity: 0, duration: 0.5 }}, (d * 4) - 0.5);
    tl.fromTo("#scene5", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, d * 4);
    tl.to("#scene5", {{ opacity: 0, duration: 0.5 }}, {duration:.1f} - 0.5);
    window.__timelines["main"] = tl;
  </script>
</body>
</html>"""
