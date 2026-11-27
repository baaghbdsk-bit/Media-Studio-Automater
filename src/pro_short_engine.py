"""Pro Vertical Short Engine (V3 Architecture) for Media Studio Automater.

Replaces static slideshows with:
1. Unconstrained Gemini-powered multi-scene visual & spoken specs (6-10 scenes, no artificial 45s cap).
2. Per-scene Neural TTS (en-US-AndrewMultilingualNeural) with exact A/V sync + faster-whisper word SRT.
3. Studio Audio Mastering: 80Hz HPF, 200Hz mud cut, 3kHz presence, 3:1 compression,
   sidechain-ducked ambient synth bed, curated SFX from assets/sfx/, and two-pass -14 LUFS loudnorm.
4. Vertical-first 1080x1920 HTML/SVG/Tailwind templates rendered deterministically via Playwright -> FFmpeg.
"""
import asyncio
import json
import os
import re
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
import numpy as np

import config

SR = 44100
DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"
FALLBACK_VOICES = ("en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-AriaNeural")

SFX_MAP = {
    "error": "error.mp3",
    "whoosh": "whoosh-short.mp3",
    "whoosh-cinematic": "whoosh-cinematic.mp3",
    "impact": "impact-bass-1.mp3",
    "impact-2": "impact-bass-2.mp3",
    "glitch": "glitch-1.mp3",
    "glitch-2": "glitch-2.mp3",
    "ping": "ping.mp3",
    "chime": "chime.mp3",
    "sparkle": "sparkle.mp3",
    "click": "click-soft.mp3",
}


def _ffmpeg_bin() -> str:
    import shutil
    return (
        shutil.which("ffmpeg")
        or r"C:\Users\vivek\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
    )


def _ffprobe_duration(path: Path) -> float:
    import shutil
    ffprobe = (
        shutil.which("ffprobe")
        or r"C:\Users\vivek\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
    )
    out = subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return float(out)


THEMES = {
    "editorial_news": {
        "bg": "#FAF9F6",
        "grid": "rgba(15, 23, 42, 0.035)",
        "card_bg": "#FFFFFF",
        "card_border": "#E5E7EB",
        "caption_bg": "#FFFFFF",
        "caption_border": "#1E293B",
        "hud_style": "editorial",
    },
    "blueprint_arch": {
        "bg": "#F4F8FF",
        "grid": "rgba(37, 99, 235, 0.065)",
        "card_bg": "#FFFFFF",
        "card_border": "#BFDBFE",
        "caption_bg": "#FFFFFF",
        "caption_border": "#3B82F6",
        "hud_style": "blueprint",
    },
    "kinetic_split": {
        "bg": "#FFFFFF",
        "grid": "rgba(15, 23, 42, 0.03)",
        "card_bg": "#F8FAFC",
        "card_border": "#0F172A",
        "caption_bg": "#0F172A",
        "caption_border": "#0F172A",
        "caption_text": "#FFFFFF",
        "hud_style": "kinetic",
    },
    "product_ui": {
        "bg": "#F8FAFC",
        "grid": "rgba(15, 23, 42, 0.045)",
        "card_bg": "#FFFFFF",
        "card_border": "#E2E8F0",
        "caption_bg": "#FFFFFF",
        "caption_border": "#CBD5E1",
        "hud_style": "product",
    },
}


def _sanitize_svg(raw_svg: str) -> str:
    """Ensure LLM-generated SVG is safe, self-contained, and scales cleanly."""
    if not raw_svg or "<svg" not in raw_svg.lower():
        return ""
    cleaned = re.sub(r"<script[\s\S]*?</script>", "", raw_svg, flags=re.IGNORECASE)
    cleaned = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.IGNORECASE)
    m = re.search(r"<svg[\s\S]*?</svg>", cleaned, flags=re.IGNORECASE)
    if not m:
        return ""
    svg = m.group(0)
    if "viewBox" not in svg:
        svg = svg.replace("<svg", '<svg viewBox="0 0 900 540"', 1)
    svg = re.sub(r'<svg([^>]*)>', lambda g: '<svg' + re.sub(r'\s(width|height)\s*=\s*["\'][^"\']*["\']', '', g.group(1)) + ' class="w-full h-auto max-h-[680px]">', svg, count=1)
    return svg


def generate_scene_spec(topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an unconstrained, visually unique Light-Mode JSON spec via Gemini (with deterministic fallback)."""
    api_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    model_name = getattr(config, "GEMINI_MODEL", "gemini-3.5-flash") or "gemini-3.5-flash"

    title = str(topic_data.get("title") or "How Modern AI Systems Work")
    summary = str(topic_data.get("summary") or "")
    hook = str(topic_data.get("hook") or "")
    pillar = str(topic_data.get("pillar") or "TECH")
    qa_feedback = str(topic_data.get("qa_feedback") or "").strip()

    if api_key:
        feedback_block = (
            f"\nPREVIOUS RENDER FAILED QA — FIX THESE SPECIFIC ISSUES:\n{qa_feedback}\n"
            if qa_feedback
            else ""
        )
        prompt = f"""You are an elite motion-graphics director (Vox, Kurzgesagt, Apple Keynote, ByteByteGo).
Create a visually UNIQUE, Light-Mode 9:16 vertical explainer video spec for:
Title: {title}
Pillar: {pillar}
Hook: {hook}
Summary: {summary}
{feedback_block}

CRITICAL ART DIRECTION RULES:
1. Pick the BEST `theme` for this topic (do NOT use the same look for every topic):
   - "editorial_news": Warm magazine style for AI news, policy, or consumer product updates.
   - "blueprint_arch": Technical drafting grid for databases, networking, RAG, or system architecture.
   - "kinetic_split": Bold high-contrast black-bordered cards for comparisons, benchmarks, or myth-busting.
   - "product_ui": Clean Apple-style app UI cards for tools, workflows, and tutorials.
2. NEVER invent fake CLI commands or fake code if the topic is consumer/product news (e.g., pricing, usage limits, company mergers). Use `custom_svg` visual metaphors, app UI mockups, gauges, or `compare_stack` instead!
3. Include at least 2 `"custom_svg"` scenes with bespoke, crisp Light-Mode SVG illustrations (`viewBox="0 0 900 540"`, light backgrounds `#FFFFFF`/`#F8FAFC`, dark readable text `#0F172A`, bold colored shapes/arrows/gauges/tanks/UI mockups, minimum `font-size="22"` inside SVG).
4. HOOK & MOBILE SAFE ZONES: Scene 1 (0-2s) MUST open with a scroll-stopping 3-6 word visual hook (surprising stat, concrete contrast, or sharp question) — never a generic intro. Keep all primary text/diagrams centered with generous margins so YouTube Shorts / Instagram Reels bottom & right-edge UI buttons never cover key labels.
4. Unconstrained length: 5 to 8 scenes (~45-95s) so the topic is explained clearly without fluff or AI clichés.
5. Every scene MUST use one of these templates and match its exact `data` schema:
   - "custom_svg": {{"card_title": str, "svg": "<svg viewBox='0 0 900 540'>...</svg>", "takeaway_pill": str}}
   - "terminal_card": {{"prompt": str, "output": str, "badge": str, "stamped": bool, "stamp_text": str, "footer_label": str, "footer_value": str}} (ONLY for actual coding/LLM prompt topics!)
   - "prob_bars": {{"query": str, "bars": [{{"label": str, "pct": int, "color": "rose"|"amber"|"cyan"|"emerald"|"slate"}}]}}
   - "pipeline_steps": {{"source_title": str, "source_sub": str, "source_tag": str, "items": [{{"tag": str, "text": str, "meta": str, "highlight": bool}}]}}
   - "compare_stack": {{"top_title": str, "top_badge": str, "top_left": str, "top_right": str, "bot_title": str, "bot_badge": str, "bot_lines": [str, str]}}
   - "vector_plot": {{"q_label": str, "match_label": str, "other_label": str, "angle_text": str, "footer_title": str, "footer_sub": str, "footer_metric": str}}
   - "code_diff": {{"system_line": str, "injected_lines": [str], "user_line": str, "answer_text": str, "answer_badge": str}}
   - "scorecard": {{"col_a": str, "col_b": str, "rows": [{{"metric": str, "val_a": str, "val_b": str}}], "hero_title": str, "hero_sub": str}}

Output ONLY valid JSON matching:
{{
  "title": "{title}",
  "theme": "editorial_news" | "blueprint_arch" | "kinetic_split" | "product_ui",
  "scenes": [
    {{
      "hud_label": "01 // SHORT LABEL",
      "accent": "rose" | "amber" | "cyan" | "violet" | "emerald",
      "eyebrow": "SHORT TAG",
      "headline": "TWO TO FIVE WORDS",
      "template": "custom_svg",
      "data": {{...}},
      "sfx": "error" | "whoosh" | "whoosh-cinematic" | "impact" | "glitch" | "ping" | "chime" | "sparkle" | "none",
      "spoken": "Natural spoken sentences for this scene.",
      "caption": "Punchy on-screen caption.",
      "highlight": "key phrase inside caption"
    }}
  ]
}}"""
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            candidates = []
            for m_name in (model_name, "gemini-3.5-flash-lite", "gemini-2.5-flash"):
                if m_name and m_name not in candidates:
                    candidates.append(m_name)
            for m_name in candidates:
                try:
                    resp = client.models.generate_content(model=m_name, contents=prompt)
                    raw = resp.text or ""
                    m = re.search(r"\{[\s\S]*\}", raw)
                    if m:
                        parsed = json.loads(m.group(0))
                        if isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 4:
                            return parsed
                except Exception as m_exc:
                    print(f"[ProShortEngine] Gemini {m_name} failed: {m_exc}")
        except Exception as exc:
            print(f"[ProShortEngine] Gemini client error, using deterministic fallback: {exc}")

    return _deterministic_scene_spec(topic_data)


def _deterministic_scene_spec(topic_data: Dict[str, Any]) -> Dict[str, Any]:
    title = str(topic_data.get("title") or "Tech Update")
    hook = str(topic_data.get("hook") or f"Here is what changed in {title}.")
    summary = str(topic_data.get("summary") or hook)
    problem = str(topic_data.get("problem") or f"Old workflows split context and hide limits.")
    solution = str(topic_data.get("solution") or f"The new unified approach tracks everything in one place.")
    example = str(topic_data.get("example") or summary)
    takeaway = str(topic_data.get("takeaway") or f"Adapt your workflow early to {title}.")
    return {
        "title": title,
        "scenes": [
            {
                "hud_label": "01 // THE SHIFT",
                "accent": "rose",
                "eyebrow": "BREAKING CHANGE",
                "headline": title[:28].upper(),
                "template": "terminal_card",
                "data": {
                    "prompt": f"Check impact: {title}",
                    "output": hook[:110],
                    "badge": "LIVE UPDATE",
                    "stamped": True,
                    "stamp_text": "LIMIT RISK",
                    "footer_label": "KEY IMPACT:",
                    "footer_value": "WORKFLOW CHANGE",
                },
                "sfx": "error",
                "spoken": hook,
                "caption": hook,
                "highlight": title.split()[0] if title.split() else "",
            },
            {
                "hud_label": "02 // THE PROBLEM",
                "accent": "amber",
                "eyebrow": "WHY IT MATTERS",
                "headline": "THE HIDDEN BOTTLENECK.",
                "template": "compare_stack",
                "data": {
                    "top_title": "OLD WORKFLOW",
                    "top_badge": "FRAGMENTED",
                    "top_left": problem[:55],
                    "top_right": "Hidden limits",
                    "bot_title": "NEW SYSTEM",
                    "bot_badge": "UNIFIED",
                    "bot_lines": [solution[:75], example[:75]],
                },
                "sfx": "whoosh",
                "spoken": f"{problem} {solution}",
                "caption": problem,
                "highlight": "limits",
            },
            {
                "hud_label": "03 // REAL EXAMPLE",
                "accent": "cyan",
                "eyebrow": "IN PRACTICE",
                "headline": "HOW IT AFFECTS YOU.",
                "template": "pipeline_steps",
                "data": {
                    "source_title": title[:34],
                    "source_sub": "Real-world workflow impact",
                    "source_tag": "ACTIVE",
                    "items": [
                        {"tag": "STEP 01", "text": summary[:68], "meta": "Input", "highlight": False},
                        {"tag": "STEP 02", "text": example[:68], "meta": "Impact", "highlight": True},
                        {"tag": "STEP 03", "text": takeaway[:68], "meta": "Action", "highlight": False},
                    ],
                },
                "sfx": "impact",
                "spoken": example,
                "caption": example,
                "highlight": "pool",
            },
            {
                "hud_label": "04 // THE TAKEAWAY",
                "accent": "emerald",
                "eyebrow": "ACTION PLAN",
                "headline": "STAY AHEAD.",
                "template": "scorecard",
                "data": {
                    "col_a": "PREPARED",
                    "col_b": "UNPREPARED",
                    "rows": [
                        {"metric": "VISIBILITY", "val_a": "Tracked", "val_b": "Blind"},
                        {"metric": "UPTIME", "val_a": "Protected", "val_b": "Rate-Limited"},
                    ],
                    "hero_title": takeaway[:46].upper(),
                    "hero_sub": "MONITOR YOUR USAGE EARLY",
                },
                "sfx": "chime",
                "spoken": takeaway,
                "caption": takeaway,
                "highlight": "consumption",
            },
        ],
    }


async def _tts_save(text: str, out_path: Path, voice: str) -> None:
    comm = edge_tts.Communicate(text, voice, rate="+4%")
    await comm.save(str(out_path))


def synthesize_scenes(scenes: List[Dict[str, Any]], work_dir: Path) -> Tuple[List[Dict[str, Any]], Path, List[Dict[str, Any]]]:
    """Synthesize per-scene TTS for exact A/V timing + faster-whisper word timestamps for SRT."""
    ffmpeg = _ffmpeg_bin()
    audio_dir = work_dir / "scene_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    timings: List[Dict[str, Any]] = []
    concat_inputs: List[Path] = []
    cursor = 0.0
    gap = 0.22

    # Generate silence gap wav
    gap_wav = audio_dir / "gap.wav"
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", str(gap), "-c:a", "pcm_s16le", str(gap_wav)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )

    for idx, sc in enumerate(scenes):
        mp3_path = audio_dir / f"scene_{idx:02d}.mp3"
        wav_path = audio_dir / f"scene_{idx:02d}.wav"
        spoken = str(sc.get("spoken") or "").strip() or str(sc.get("caption") or "Next step.")

        ok = False
        for v in (DEFAULT_VOICE, *FALLBACK_VOICES):
            try:
                asyncio.run(_tts_save(spoken, mp3_path, v))
                if mp3_path.exists() and mp3_path.stat().st_size > 512:
                    ok = True
                    break
            except Exception as exc:
                print(f"[ProShortEngine] TTS {v} failed on scene {idx}: {exc}")
        if not ok:
            raise RuntimeError(f"All TTS voices failed on scene {idx}")

        subprocess.run(
            [ffmpeg, "-y", "-i", str(mp3_path), "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        dur = _ffprobe_duration(wav_path)
        start_s = cursor
        end_s = cursor + dur + gap
        timings.append({"index": idx, "start": round(start_s, 3), "end": round(end_s, 3), "dur": round(dur, 3)})
        concat_inputs.append(wav_path)
        concat_inputs.append(gap_wav)
        cursor = end_s

    list_txt = audio_dir / "concat.txt"
    list_txt.write_text("\n".join(f"file '{p.as_posix()}'" for p in concat_inputs), encoding="utf-8")
    raw_vo_wav = work_dir / "voice_concat.wav"
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt), "-c:a", "pcm_s16le", str(raw_vo_wav)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )

    # Extract word timestamps via faster-whisper using ffmpeg PCM pipe (avoids PyAV metadata_errors)
    words: List[Dict[str, Any]] = []
    try:
        from faster_whisper import WhisperModel
        pcm_bytes = subprocess.check_output(
            [ffmpeg, "-i", str(raw_vo_wav), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
            stderr=subprocess.DEVNULL,
        )
        audio_np = np.frombuffer(pcm_bytes, dtype=np.float32)
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        segs, _ = model.transcribe(audio_np, word_timestamps=True)
        for seg in segs:
            for w in (seg.words or []):
                words.append({"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})
    except Exception as exc:
        print(f"[ProShortEngine] faster-whisper fallback to scene captions for SRT: {exc}")
        for idx, sc in enumerate(scenes):
            words.append({"text": sc.get("caption", ""), "start": timings[idx]["start"], "end": timings[idx]["end"]})

    return timings, raw_vo_wav, words


def build_studio_audio(
    scenes: List[Dict[str, Any]],
    timings: List[Dict[str, Any]],
    raw_vo_wav: Path,
    work_dir: Path,
    out_audio_path: Path,
) -> float:
    """Apply vocal EQ/compressor, sidechain-ducked ambient synth bed, curated SFX, and -14 LUFS two-pass loudnorm."""
    ffmpeg = _ffmpeg_bin()
    total_dur = max(5.0, timings[-1]["end"]) if timings else 10.0
    n_samples = int(SR * total_dur)
    t = np.linspace(0, total_dur, n_samples, endpoint=False)

    # 1. Warm dark-tech ambient synth bed
    root = np.where(t < total_dur * 0.3, 73.42, np.where(t < total_dur * 0.65, 58.27, 65.41))
    bed = (
        0.45 * np.sin(2 * np.pi * root * t)
        + 0.25 * np.sin(2 * np.pi * (root * 1.498) * t)
        + 0.15 * np.sin(2 * np.pi * (root * 2.0) * t)
    )
    pulse = 0.55 + 0.45 * np.sin(2 * np.pi * 1.0 * t) ** 2
    fade_in = np.minimum(1.0, t / 1.2)
    fade_out = np.minimum(1.0, (total_dur - t) / 1.5)
    bed = np.clip(bed * pulse * 0.10 * fade_in * fade_out, -0.95, 0.95)
    bed_wav = work_dir / "ambient_bed.wav"
    with wave.open(str(bed_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((bed * 32767).astype(np.int16).tobytes())

    # 2. Place curated SFX from project assets/sfx/
    sfx_dir = Path(__file__).resolve().parent.parent / "assets" / "sfx"
    sfx_mix = np.zeros(n_samples, dtype=np.float64)
    for idx, sc in enumerate(scenes):
        sfx_key = str(sc.get("sfx") or "none").lower()
        fname = SFX_MAP.get(sfx_key)
        if not fname:
            continue
        sfx_path = sfx_dir / fname
        if not sfx_path.exists():
            continue
        raw = subprocess.check_output(
            [ffmpeg, "-i", str(sfx_path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
            stderr=subprocess.DEVNULL,
        )
        arr = np.frombuffer(raw, dtype=np.float32)
        start_idx = int((timings[idx]["start"] + 0.04) * SR)
        end_idx = min(n_samples, start_idx + len(arr))
        if start_idx < n_samples and end_idx > start_idx:
            sfx_mix[start_idx:end_idx] += arr[: end_idx - start_idx] * 0.30

    sfx_wav = work_dir / "sfx_track.wav"
    with wave.open(str(sfx_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(sfx_mix, -0.95, 0.95) * 32767).astype(np.int16).tobytes())

    # 3. Mix + Sidechain Ducking
    premix_wav = work_dir / "audio_premix.wav"
    filter_complex = (
        f"[0:a]aresample={SR},highpass=f=80,"
        "equalizer=f=200:width_type=o:width=1:g=-3,"
        "equalizer=f=3000:width_type=o:width=1:g=3,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=50:makeup=2,"
        "asplit=2[vo][vo_sc];"
        f"[1:a]aresample={SR}[bed];"
        "[bed][vo_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[bed_ducked];"
        f"[2:a]aresample={SR}[sfx];"
        "[vo][bed_ducked][sfx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=-1.5dB[pre]"
    )
    subprocess.run([
        ffmpeg, "-y", "-i", str(raw_vo_wav), "-i", str(bed_wav), "-i", str(sfx_wav),
        "-filter_complex", filter_complex, "-map", "[pre]", "-c:a", "pcm_s16le", str(premix_wav),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 4. Two-Pass Loudness Normalization (-14 LUFS / -1.0 dBTP)
    p1 = subprocess.run(
        [ffmpeg, "-y", "-i", str(premix_wav), "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json", "-f", "null", "NUL" if os.name == "nt" else "/dev/null"],
        capture_output=True, text=True, check=True,
    )
    m = re.search(r"\{[\s\S]*\}", p1.stderr)
    if m:
        stats = json.loads(m.group(0))
        ln_filter = (
            f"loudnorm=I=-14:TP=-1.0:LRA=11:linear=true:"
            f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
            f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
            f"offset={stats['target_offset']}"
        )
    else:
        ln_filter = "loudnorm=I=-14:TP=-1.0:LRA=11"

    ext = out_audio_path.suffix.lower()
    codec_args = ["-c:a", "pcm_s16le"] if ext == ".wav" else ["-c:a", "aac", "-b:a", "192k"]
    subprocess.run(
        [ffmpeg, "-y", "-i", str(premix_wav), "-af", ln_filter, *codec_args, str(out_audio_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    return total_dur


def build_pro_html(spec: Dict[str, Any], timings: List[Dict[str, Any]], total_dur: float) -> str:
    """Build deterministic 1080x1920 vertical-first HTML with dynamic theme & custom SVG support."""
    theme_key = str(spec.get("theme") or "product_ui")
    theme = THEMES.get(theme_key, THEMES["product_ui"])
    cap_text = theme.get("caption_text", "#0F172A")

    timeline_payload = []
    for idx, sc in enumerate(spec["scenes"]):
        sc_copy = dict(sc)
        if sc_copy.get("template") == "custom_svg":
            d = dict(sc_copy.get("data") or {})
            d["svg"] = _sanitize_svg(str(d.get("svg") or ""))
            sc_copy["data"] = d
        timeline_payload.append({**sc_copy, "start": timings[idx]["start"], "end": timings[idx]["end"]})
    payload_json = json.dumps(timeline_payload, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1920, initial-scale=1.0">
  <title>{spec.get('title', 'Tech Short')}</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700;800&family=JetBrains+Mono:wght@600;700;800&family=Inter:wght@600;700;800;900&display=swap');
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: 1080px; height: 1920px; background: {theme['bg']}; font-family: 'Inter', sans-serif; overflow: hidden; color: #0F172A; }}
    .font-display {{ font-family: 'Space Grotesk', sans-serif; }}
    .font-mono-tech {{ font-family: 'JetBrains Mono', monospace; }}
    .bg-grid {{ background-image: linear-gradient(to right, {theme['grid']} 1px, transparent 1px), linear-gradient(to bottom, {theme['grid']} 1px, transparent 1px); background-size: 60px 60px; }}
    .glass-card {{ background: {theme['card_bg']}; border: 2px solid {theme['card_border']}; box-shadow: 0 20px 45px -12px rgba(15,23,42,0.10); }}
  </style>
</head>
<body class="relative bg-grid flex flex-col justify-between px-12 pt-14 pb-[270px]">
  <div id="glow-top" class="absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[550px] rounded-full bg-sky-500/10 blur-[140px] pointer-events-none"></div>
  <div class="relative z-20 flex items-center justify-between border-b-2 border-slate-200 pb-4">
    <div class="flex items-center gap-4">
      <span id="hud-dot" class="w-4 h-4 rounded-full bg-sky-600"></span>
      <span id="hud-section" class="font-mono-tech text-2xl font-extrabold tracking-widest text-sky-600 uppercase">01 // START</span>
    </div>
    <span id="hud-timer" class="font-mono-tech text-2xl font-bold text-slate-600 bg-white border-2 border-slate-200 px-5 py-1.5 rounded-full shadow-sm">00.0s</span>
  </div>

  <div id="stage" class="relative z-10 flex-1 flex flex-col justify-center py-4"></div>

  <div class="relative z-20 space-y-4">
    <div style="background:{theme['caption_bg']}; border-color:{theme['caption_border']}; color:{cap_text};" class="border-2 rounded-3xl px-8 py-5 shadow-xl min-h-[140px] flex items-center justify-center text-center">
      <p id="caption-box" class="text-4xl font-extrabold leading-snug tracking-tight"></p>
    </div>
    <div class="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden border border-slate-300">
      <div id="progress-bar" class="h-full bg-gradient-to-r from-sky-500 via-violet-500 to-emerald-500 w-0"></div>
    </div>
  </div>

  <script>
    const SCENES = {payload_json};
    const TOTAL = {total_dur:.3f};
    const ACCENTS = {{
      rose: ['text-rose-600', 'bg-rose-600', 'bg-rose-500/10'],
      amber: ['text-amber-600', 'bg-amber-500', 'bg-amber-500/10'],
      cyan: ['text-sky-600', 'bg-sky-600', 'bg-sky-500/10'],
      violet: ['text-violet-600', 'bg-violet-600', 'bg-violet-500/10'],
      emerald: ['text-emerald-600', 'bg-emerald-600', 'bg-emerald-500/10'],
    }};
    function clamp(v, a, b) {{ return Math.max(a, Math.min(b, v)); }}
    function easeOut(x) {{ return 1 - Math.pow(1 - clamp(x, 0, 1), 3); }}
    function esc(s) {{ return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

    function renderFrame(t) {{
      t = clamp(t, 0, TOTAL);
      document.getElementById('hud-timer').innerText = t.toFixed(1) + 's';
      document.getElementById('progress-bar').style.width = ((t / TOTAL) * 100) + '%';
      const sc = SCENES.find(s => t >= s.start && t < s.end) || SCENES[SCENES.length - 1];
      const lt = t - sc.start;
      const p = easeOut(lt / 0.6);
      const ac = ACCENTS[sc.accent] || ACCENTS.cyan;

      const hudSec = document.getElementById('hud-section');
      hudSec.innerText = sc.hud_label;
      hudSec.className = `font-mono-tech text-2xl font-extrabold tracking-widest uppercase ${{ac[0]}}`;
      document.getElementById('hud-dot').className = `w-4 h-4 rounded-full ${{ac[1]}}`;
      document.getElementById('glow-top').className = `absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[550px] rounded-full blur-[140px] pointer-events-none ${{ac[2]}}`;

      let capHtml = esc(sc.caption);
      if (sc.highlight && capHtml.includes(esc(sc.highlight))) {{
        capHtml = capHtml.replace(esc(sc.highlight), `<span class="${{ac[0]}} underline decoration-4">${{esc(sc.highlight)}}</span>`);
      }}
      document.getElementById('caption-box').innerHTML = capHtml;

      const d = sc.data || {{}};
      const header = `<div class="text-center space-y-1.5"><span class="font-mono-tech text-2xl font-bold ${{ac[0]}} tracking-widest uppercase">${{esc(sc.eyebrow)}}</span><h1 class="font-display text-6xl font-black text-slate-900 leading-tight">${{esc(sc.headline)}}</h1></div>`;
      let body = '';

      if (sc.template === 'custom_svg' && d.svg) {{
        body = `
          <div class="glass-card rounded-3xl p-6 space-y-4">
            ${{d.card_title ? `<div class="font-mono-tech text-2xl font-extrabold ${{ac[0]}} border-b border-slate-200 pb-3">${{esc(d.card_title)}}</div>` : ''}}
            <div class="rounded-2xl overflow-hidden bg-slate-50 border border-slate-200 p-3 flex items-center justify-center">${{d.svg}}</div>
            ${{d.takeaway_pill ? `<div class="text-center font-mono-tech text-2xl font-bold text-slate-800 bg-slate-100 rounded-xl py-3 px-4 border border-slate-200">${{esc(d.takeaway_pill)}}</div>` : ''}}
          </div>`;
      }} else if (sc.template === 'terminal_card') {{
        const qChars = Math.floor(easeOut(lt / 1.0) * (d.prompt || '').length);
        const aChars = lt > 1.0 ? Math.floor(easeOut((lt - 1.0) / 1.2) * (d.output || '').length) : 0;
        const stamped = d.stamped && lt >= 2.1;
        body = `
          <div class="glass-card rounded-3xl p-7 space-y-5 border-slate-200">
            <div class="bg-slate-100 rounded-2xl p-5 border border-slate-200 space-y-2"><span class="font-mono-tech text-lg text-sky-600 font-bold">PROMPT</span><p class="text-3xl font-bold text-slate-900">${{esc((d.prompt||'').slice(0,qChars))}}<span class="text-sky-600">|</span></p></div>
            <div class="bg-slate-50 rounded-2xl p-5 border-2 ${{stamped ? 'border-rose-500 bg-rose-50' : 'border-slate-200'}} space-y-3 min-h-[220px]">
              <div class="flex justify-between items-center"><span class="font-mono-tech text-lg text-violet-600 font-bold">OUTPUT</span><span class="font-mono-tech text-lg px-3 py-1 rounded bg-emerald-100 text-emerald-700 border border-emerald-300 font-bold">${{esc(d.badge)}}</span></div>
              <p class="text-3xl font-bold leading-snug ${{stamped ? 'text-rose-700 line-through decoration-rose-500 decoration-4' : 'text-slate-800'}}">${{esc((d.output||'').slice(0,aChars))}}</p>
              ${{stamped ? `<div style="transform:rotate(-4deg)" class="inline-block px-5 py-2.5 rounded-xl bg-rose-600 border-2 border-rose-300 text-white font-mono-tech text-2xl font-black shadow-lg">⚠ ${{esc(d.stamp_text || 'FABRICATED')}}</div>` : ''}}
            </div>
          </div>
          <div class="glass-card rounded-2xl p-5 flex items-center justify-between border-rose-300 bg-rose-50"><span class="font-mono-tech text-2xl font-bold text-rose-700">${{esc(d.footer_label)}}</span><span class="font-mono-tech text-3xl font-black text-slate-900">${{esc(d.footer_value)}}</span></div>`;
      }} else if (sc.template === 'prob_bars') {{
        const barsHtml = (d.bars || []).map(b => `
          <div><div class="flex justify-between font-mono-tech text-2xl font-bold mb-1"><span class="text-slate-800">${{esc(b.label)}}</span><span class="text-${{b.color}}-600">${{b.pct}}%</span></div>
          <div class="w-full h-6 bg-slate-200 rounded-full overflow-hidden"><div class="h-full bg-${{b.color}}-500" style="width:${{b.pct * p}}%"></div></div></div>`).join('');
        body = `<div class="glass-card rounded-3xl p-7 space-y-6 border-violet-200"><div class="font-mono-tech text-2xl text-slate-800 bg-slate-100 p-5 rounded-2xl border border-slate-200 font-bold">${{esc(d.query)}}</div><div class="space-y-5">${{barsHtml}}</div></div>`;
      }} else if (sc.template === 'pipeline_steps') {{
        const itemsHtml = (d.items || []).map((it, idx) => {{
          const ip = easeOut((lt - idx * 0.45) / 0.4);
          return `<div class="glass-card rounded-2xl p-5 ${{it.highlight ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200'}} flex justify-between items-center" style="opacity:${{ip}}"><div><span class="font-mono-tech text-xl font-black ${{it.highlight ? 'text-emerald-700' : 'text-sky-600'}}">${{esc(it.tag)}}</span><p class="text-2xl text-slate-900 font-semibold">${{esc(it.text)}}</p></div><span class="font-mono-tech text-xl text-slate-500 font-bold">${{esc(it.meta)}}</span></div>`;
        }}).join('');
        body = `<div class="glass-card rounded-3xl p-6 border-sky-300 bg-sky-50 flex items-center justify-between"><div><div class="font-mono-tech text-2xl font-black text-slate-900">${{esc(d.source_title)}}</div><div class="text-xl text-slate-600 font-bold">${{esc(d.source_sub)}}</div></div><span class="font-mono-tech text-xl px-4 py-2 rounded-xl bg-sky-600 text-white font-bold">${{esc(d.source_tag)}}</span></div><div class="space-y-4">${{itemsHtml}}</div>`;
      }} else if (sc.template === 'vector_plot') {{
        const radar = 25 + (lt * 100) % 130;
        body = `<div class="glass-card rounded-3xl p-5 border-emerald-300 bg-white"><svg viewBox="0 0 900 420" class="w-full h-auto bg-slate-50 rounded-2xl border border-slate-200"><line x1="70" y1="360" x2="860" y2="360" stroke="#94a3b8" stroke-width="3"/><line x1="70" y1="30" x2="70" y2="360" stroke="#94a3b8" stroke-width="3"/><circle cx="750" cy="100" r="14" fill="#64748b"/><text x="750" y="145" fill="#475569" font-family="JetBrains Mono" font-size="24" font-weight="bold" text-anchor="middle">${{esc(d.other_label)}}</text><circle cx="290" cy="185" r="${{radar}}" fill="none" stroke="#059669" stroke-width="2" stroke-opacity="0.45"/><circle cx="290" cy="185" r="130" fill="rgba(16,185,129,0.12)" stroke="#059669" stroke-width="3" stroke-dasharray="10 6"/><line x1="70" y1="360" x2="255" y2="145" stroke="#0284c7" stroke-width="5"/><line x1="70" y1="360" x2="325" y2="205" stroke="#059669" stroke-width="5"/><text x="205" y="285" fill="#b45309" font-family="JetBrains Mono" font-size="24" font-weight="bold">${{esc(d.angle_text)}}</text><circle cx="255" cy="145" r="18" fill="#0284c7"/><text x="255" y="108" fill="#0369a1" font-family="JetBrains Mono" font-size="26" font-weight="bold" text-anchor="middle">${{esc(d.q_label)}}</text><circle cx="325" cy="205" r="18" fill="#059669"/><text x="410" y="265" fill="#047857" font-family="JetBrains Mono" font-size="24" font-weight="bold" text-anchor="middle">${{esc(d.match_label)}}</text></svg></div><div class="glass-card rounded-2xl p-5 border-sky-300 bg-sky-50 flex items-center justify-between"><div><span class="font-mono-tech text-2xl font-black text-sky-700">${{esc(d.footer_title)}}</span><p class="text-xl text-slate-600 font-semibold">${{esc(d.footer_sub)}}</p></div><span class="font-mono-tech text-3xl font-black text-emerald-600">${{esc(d.footer_metric)}}</span></div>`;
      }} else if (sc.template === 'code_diff') {{
        const inj = (d.injected_lines || []).map(l => `<div>${{esc(l)}}</div>`).join('');
        body = `<div class="glass-card rounded-3xl p-7 border-emerald-400 bg-emerald-50 space-y-4 font-mono-tech text-2xl"><div class="text-slate-500 font-bold">${{esc(d.system_line)}}</div><div class="p-4 rounded-xl bg-emerald-100 border-l-8 border-emerald-600 text-emerald-900 font-bold">${{inj}}</div><div class="text-slate-900 font-bold">${{esc(d.user_line)}}</div></div><div class="glass-card rounded-3xl p-7 border-sky-300 bg-white space-y-3"><div class="flex justify-between font-mono-tech text-xl font-black"><span class="text-emerald-600">✔ VERIFIED</span><span class="text-sky-600">${{esc(d.answer_badge)}}</span></div><p class="text-3xl font-bold text-slate-900">${{esc(d.answer_text)}}</p></div>`;
      }} else if (sc.template === 'compare_stack') {{
        const botHtml = (d.bot_lines || []).map(l => `<div class="p-4 rounded-xl bg-white border border-emerald-200 text-slate-800 font-mono-tech text-2xl font-bold">${{esc(l)}}</div>`).join('');
        body = `
          <div class="glass-card rounded-3xl p-6 border-rose-300 bg-rose-50 space-y-4">
            <div class="flex items-center justify-between"><span class="font-mono-tech text-2xl font-black text-rose-700">${{esc(d.top_title)}}</span><span class="font-mono-tech text-xl font-black px-4 py-1 rounded-lg bg-rose-600 text-white">${{esc(d.top_badge)}}</span></div>
            <div class="grid grid-cols-2 gap-4 font-mono-tech text-2xl">
              <div class="p-4 rounded-xl bg-white border border-rose-200 text-slate-900 font-bold">${{esc(d.top_left)}}</div>
              <div class="p-4 rounded-xl bg-white border border-rose-200 text-rose-700 font-bold">${{esc(d.top_right)}}</div>
            </div>
          </div>
          <div class="glass-card rounded-3xl p-6 border-emerald-400 bg-emerald-50 space-y-4">
            <div class="flex items-center justify-between"><span class="font-mono-tech text-2xl font-black text-emerald-700">${{esc(d.bot_title)}}</span><span class="font-mono-tech text-xl font-black px-4 py-1 rounded-lg bg-emerald-600 text-white">${{esc(d.bot_badge)}}</span></div>
            <div class="space-y-3">${{botHtml}}</div>
          </div>`;
      }} else {{
        const rowsHtml = (d.rows || []).map(r => `<div class="grid grid-cols-3 p-5 text-2xl font-bold border-b border-slate-200"><span class="text-slate-700">${{esc(r.metric)}}</span><span class="text-emerald-600 font-mono-tech">${{esc(r.val_a)}}</span><span class="text-rose-600 font-mono-tech">${{esc(r.val_b)}}</span></div>`).join('');
        body = `<div class="glass-card rounded-3xl overflow-hidden border-slate-300"><div class="grid grid-cols-3 bg-slate-100 p-5 font-mono-tech text-2xl font-black border-b border-slate-200"><span class="text-slate-500">METRIC</span><span class="text-emerald-600">${{esc(d.col_a || 'A')}}</span><span class="text-rose-600">${{esc(d.col_b || 'B')}}</span></div>${{rowsHtml}}</div><div class="rounded-3xl p-7 bg-gradient-to-r from-emerald-50 via-sky-50 to-violet-50 border-2 border-emerald-500 text-center space-y-2 shadow-lg"><h2 class="font-display text-4xl font-black text-slate-900">${{esc(d.hero_title)}}</h2><p class="font-mono-tech text-2xl text-emerald-700 font-bold">${{esc(d.hero_sub)}}</p></div>`;
      }}

      stage.innerHTML = `<div class="flex flex-col gap-6 w-full" style="opacity:${{p}}">${{header}}${{body}}</div>`;
      stage.querySelectorAll('svg').forEach(svg => {{
        const vb = svg.viewBox && svg.viewBox.baseVal ? svg.viewBox.baseVal : {{ x: 0, y: 0, width: 900, height: 540 }};
        const rects = Array.from(svg.querySelectorAll('rect')).map(r => {{
          const b = r.getBBox();
          return {{ x: b.x, y: b.y, w: b.width, h: b.height, area: b.width * b.height }};
        }}).filter(r => r.w > 30 && r.h > 18 && r.w < vb.width * 0.92);
        svg.querySelectorAll('text').forEach(txt => {{
          const tb = txt.getBBox();
          if (!tb || tb.width <= 0) return;
          const cx = tb.x + tb.width / 2, cy = tb.y + tb.height / 2;
          const box = rects.filter(r => cx >= r.x && cx <= r.x + r.w && cy >= r.y && cy <= r.y + r.h).sort((a, b) => a.area - b.area)[0] || {{ x: vb.x + 16, y: vb.y + 16, w: vb.width - 32, h: vb.height - 32 }};
          const maxW = Math.max(40, box.w - 24);
          if (tb.width > maxW) {{
            const cs = window.getComputedStyle(txt);
            const curFs = parseFloat(txt.getAttribute('font-size') || cs.fontSize || '20') || 20;
            const newFs = Math.max(11, curFs * (maxW / tb.width) * 0.96);
            txt.setAttribute('font-size', newFs.toFixed(1));
            txt.style.fontSize = newFs.toFixed(1) + 'px';
          }}
          const nb = txt.getBBox();
          if (nb.x < box.x + 10) {{
            const oldX = parseFloat(txt.getAttribute('x') || '0');
            if (!isNaN(oldX)) txt.setAttribute('x', (oldX + (box.x + 10 - nb.x)).toFixed(1));
          }} else if (nb.x + nb.width > box.x + box.w - 10) {{
            const oldX = parseFloat(txt.getAttribute('x') || '0');
            if (!isNaN(oldX)) txt.setAttribute('x', (oldX - (nb.x + nb.width - (box.x + box.w - 10))).toFixed(1));
          }}
        }});
      }});
    }}

    window.renderFrame = renderFrame;
    renderFrame(0);
  </script>
</body>
</html>"""


def render_deterministic_mp4(html_path: Path, audio_path: Path, out_mp4: Path, total_dur: float, fps: int = 24) -> None:
    """Render HTML deterministically frame-by-frame via Playwright piped to FFmpeg."""
    from playwright.sync_api import sync_playwright
    ffmpeg = _ffmpeg_bin()
    total_frames = max(1, int(fps * total_dur))

    ffmpeg_cmd = [
        ffmpeg, "-y",
        "-f", "image2pipe", "-vcodec", "png", "-r", str(fps), "-i", "-",
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest", str(out_mp4),
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_timeout(400)
        for i in range(total_frames):
            t = i / fps
            page.evaluate(f"window.renderFrame({t:.4f})")
            proc.stdin.write(page.screenshot(type="png"))
        browser.close()
    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg deterministic render failed with code {ret}")
