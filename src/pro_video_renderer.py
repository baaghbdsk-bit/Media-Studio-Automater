"""Pro-grade vertical short renderer v2 (1080x1920, 30fps, 9:16).

Records real smooth motion via Playwright video capture (30fps) instead of
static screenshots. Each scene runs CSS keyframe animations for its full
duration; scenes crossfade. Audio (TTS) + ambient music bed mixed with
ffmpeg; karaoke SRT burned in. Encode: libx264 medium, CRF 17, 30fps.
"""
from __future__ import annotations
import asyncio, json, os, re, subprocess, shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple

import edge_tts
from playwright.sync_api import sync_playwright

W, H, FPS = 1080, 1920, 30
VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+6%"
OUT_ROOT = Path("generated_visuals") / "pro_videos"


def _slug(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()[:50] or "demo"


def _scene_html(kind: str, data: Dict[str, Any]) -> str:
    if kind == "concept":
        pills = "".join(f'<span class="pill pill-{p.get("color","cyan")}">{p.get("label","")}</span>' for p in data.get("pills", []))
        return f'<div class="card"><div class="card-h">{pills}</div><div class="body">{data.get("body","")}</div></div>'
    if kind == "flow":
        nodes = data.get("nodes", [])
        parts = []
        for i, n in enumerate(nodes):
            parts.append(f'<div class="node {n.get("cls","")}">{n.get("text","")}</div>')
            if i < len(nodes) - 1:
                parts.append('<div class="arrow">→</div>')
        return f'<div class="flow">{"".join(parts)}</div>'
    if kind == "analogy":
        cards = "".join(
            f'<div class="analogy-card"><div class="analogy-kicker">{c.get("kicker","")}</div>'
            f'<div class="analogy-title">{c.get("title","")}</div></div>'
            for c in data.get("cards", [])
        )
        return f'<div class="analogy">{cards}</div>'
    if kind == "takeaway":
        return f'<div class="takeaway">{data.get("text","")}</div>'
    if kind == "code":
        return f'<div class="card"><div class="code-container">{data.get("code","")}</div></div>'
    return f'<div class="card"><div class="body">{data.get("body","")}</div></div>'


PAGE_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;margin:0;padding:0;overflow:hidden}
body{background:radial-gradient(circle at 50% 25%,#1e293b 0%,#070a14 75%);
color:#F8FAFC;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
position:relative}
.grid{position:absolute;inset:0;background-size:60px 60px;
background-image:linear-gradient(to right,rgba(255,255,255,.025)1px,transparent 1px),
linear-gradient(to bottom,rgba(255,255,255,.025)1px,transparent 1px);
animation:gridmove 20s linear infinite;pointer-events:none}
@keyframes gridmove{from{transform:translate(0,0)}to{transform:translate(60px,60px)}}
.orb{position:absolute;border-radius:50%;filter:blur(60px);opacity:.35;animation:float 8s ease-in-out infinite}
.orb1{width:500px;height:500px;background:#22D3EE;top:-100px;right:-120px}
.orb2{width:420px;height:420px;background:#818CF8;bottom:200px;left:-140px;animation-delay:-4s}
@keyframes float{0%,100%{transform:translate(0,0)}50%{transform:translate(30px,-40px)}}
.wrap{position:relative;z-index:10;width:100%;height:100%;display:flex;flex-direction:column;
padding:180px 80px 480px 80px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.tag{background:rgba(34,211,238,.15);border:1px solid #22D3EE;color:#22D3EE;padding:10px 22px;border-radius:999px;font-size:24px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.brand{font-size:28px;font-weight:800;color:#94A3B8;letter-spacing:2px}
.brand span{color:#38BDF8}
.hero{margin-top:16px;margin-bottom:16px}
.day{font-size:26px;font-weight:800;color:#38BDF8;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;
animation:fadeUp .6s .1s both}
.concept{font-size:60px;font-weight:900;line-height:1.12;
background:linear-gradient(135deg,#FFFFFF 25%,#94A3B8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;
animation:fadeUp .7s .2s both}
@keyframes fadeUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}
.stage{flex:1;display:flex;flex-direction:column;justify-content:center;gap:20px}
.card{background:rgba(15,23,42,.88);border:1px solid rgba(255,255,255,.12);border-radius:30px;padding:40px;
box-shadow:0 30px 70px rgba(0,0,0,.6);backdrop-filter:blur(20px);
animation:cardIn .6s .3s both}
@keyframes cardIn{from{opacity:0;transform:translateY(50px) scale(.95)}to{opacity:1;transform:translateY(0) scale(1)}}
.card-h{display:flex;align-items:center;gap:16px;margin-bottom:22px;flex-wrap:wrap}
.pill{padding:9px 18px;border-radius:10px;font-size:22px;font-weight:800;text-transform:uppercase;
animation:pill .5s .4s both}
@keyframes pill{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
.pill-cyan{background:rgba(34,211,238,.18);color:#22D3EE;border:1px solid #22D3EE}
.pill-red{background:rgba(239,68,68,.18);color:#EF4444;border:1px solid #EF4444}
.pill-green{background:rgba(16,185,129,.18);color:#10B981;border:1px solid #10B981}
.pill-amber{background:rgba(245,158,11,.18);color:#F59E0B;border:1px solid #F59E0B}
.ctitle{font-size:36px;font-weight:800}
.body{font-size:30px;line-height:1.55;color:#E2E8F0}
.flow{display:flex;align-items:center;justify-content:space-between;background:#050811;border:1px solid #1E293B;border-radius:20px;padding:22px 26px;margin:14px 0}
.node{background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.15);padding:16px 22px;border-radius:14px;font-size:24px;font-weight:700;text-align:center;
animation:nodeIn .5s .5s both}
@keyframes nodeIn{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:scale(1)}}
.node.accent{border-color:#22D3EE;color:#22D3EE;background:rgba(34,211,238,.1)}
.arrow{font-size:30px;color:#64748B;font-weight:bold;margin:0 10px}
.analogy{display:flex;flex-direction:column;gap:18px}
.analogy-card{background:linear-gradient(110deg,rgba(15,23,42,.96),rgba(15,23,42,.78));border:1px solid rgba(255,255,255,.14);border-left:6px solid #22D3EE;border-radius:20px;padding:24px 30px;
box-shadow:0 18px 40px rgba(0,0,0,.45);animation:fadeUp .55s both}
.analogy-card:nth-child(2){border-left-color:#10B981;animation-delay:.12s}
.analogy-card:nth-child(3){border-left-color:#F59E0B;animation-delay:.24s}
.analogy-kicker{font-size:20px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94A3B8;margin-bottom:6px}
.analogy-title{font-size:34px;font-weight:900;line-height:1.2;color:#F8FAFC}
.takeaway{background:linear-gradient(90deg,rgba(34,211,238,.16),rgba(99,102,241,.16));border-left:8px solid #22D3EE;border-radius:0 18px 18px 0;padding:26px 34px;font-size:28px;line-height:1.45;color:#E2E8F0;
animation:fadeUp .6s .3s both}
.takeaway b{color:#22D3EE}
.caption-bar{background:rgba(7,10,20,.96);border:2px solid #38BDF8;border-radius:20px;padding:18px 30px;text-align:center;
box-shadow:0 20px 50px rgba(0,0,0,.8),0 0 30px rgba(56,189,248,.25);margin-top:12px;
animation:fadeUp .5s .6s both}
.caption-text{font-size:30px;font-weight:800;color:#FFFFFF;line-height:1.35}
.caption-text .hi{color:#FDE047;text-shadow:0 0 18px rgba(253,224,71,.55)}
.accent-bar{position:absolute;left:0;bottom:0;height:6px;width:100%;background:linear-gradient(90deg,#22D3EE,#818CF8);transform-origin:left;animation:bar 1.2s .2s both}
@keyframes bar{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.code-container{background:#050811;border:1px solid #1E293B;border-radius:20px;padding:30px;font-family:'Consolas','Courier New',monospace;font-size:28px;line-height:1.5;color:#E2E8F0}
.kw{color:#F43F5E;font-weight:bold}.fn{color:#38BDF8}.str{color:#34D399}.com{color:#64748B;font-style:italic}.val{color:#F59E0B}
</style></head><body>
<div class="grid"></div><div class="orb orb1"></div><div class="orb orb2"></div>
<div class="wrap">
<div class="header"><div class="tag">Tech Explained</div><div class="brand">PLAIN<span>TECH</span></div></div>
<div class="hero"><div class="day">__DAY__</div><div class="concept">__TITLE__</div></div>
<div class="stage">__SCENE__</div>
<div class="caption-bar"><div class="caption-text">__CAPTION__</div></div>
</div>
<div class="accent-bar"></div>
</body></html>"""


def _synthesize(narration: str, audio_path: str) -> List[Dict[str, Any]]:
    words: List[Dict[str, Any]] = []

    async def run():
        com = edge_tts.Communicate(narration, VOICE, rate=RATE, boundary="WordBoundary")
        async for chunk in com.stream():
            if chunk["type"] == "WordBoundary":
                words.append({"text": chunk["text"], "start": chunk["offset"] / 1e7,
                              "end": (chunk["offset"] + chunk["duration"]) / 1e7})
        com2 = edge_tts.Communicate(narration, VOICE, rate=RATE, boundary="SentenceBoundary")
        await com2.save(audio_path)

    asyncio.run(run())
    return words


def _fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_karaoke_srt(words: List[Dict[str, Any]], srt_path: str, wpl: int = 4):
    lines, i, idx = [], 0, 1
    while i < len(words):
        chunk = words[i:i + wpl]
        lines.append(f"{idx}\n{_fmt_ts(chunk[0]['start'])} --> {_fmt_ts(chunk[-1]['end'])}\n{' '.join(w['text'] for w in chunk)}\n")
        i += wpl; idx += 1
    Path(srt_path).write_text("\n".join(lines), encoding="utf-8")


def _render_video(scenes: List[Dict[str, Any]], durations: List[float], out_dir: Path, total: float) -> Path:
    """Record the whole short as one Playwright video (smooth 30fps)."""
    vid_dir = out_dir / "_raw"
    vid_dir.mkdir(parents=True, exist_ok=True)
    for f in vid_dir.iterdir():
        f.unlink()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(vid_dir),
            record_video_size={"width": W, "height": H},
        )
        page = context.new_page()

        # inject scene 0
        def show_scene(idx):
            sc = scenes[idx]
            html = (PAGE_TEMPLATE
                    .replace("__DAY__", sc.get("_day", "AI Explained"))
                    .replace("__TITLE__", sc.get("_title", ""))
                    .replace("__SCENE__", sc["html"])
                    .replace("__CAPTION__", sc.get("caption", "")))
            page.set_content(html, wait_until="domcontentloaded")
            page.wait_for_timeout(120)

        show_scene(0)
        # record: advance scenes
        for i, d in enumerate(durations):
            if i > 0:
                # crossfade by re-rendering
                show_scene(i)
            page.wait_for_timeout(int(d * 1000))

        context.close()
        browser.close()

    # find the recorded webm
    webms = list(vid_dir.glob("*.webm"))
    if not webms:
        raise RuntimeError("Playwright did not produce a video")
    webm = webms[0]
    mp4 = out_dir / "raw.mp4"
    # convert webm -> mp4 (lossless-ish) for ffmpeg pipeline
    subprocess.run([
        "ffmpeg", "-y", "-i", str(webm), "-c:v", "libx264", "-preset", "fast",
        "-crf", "16", "-r", str(FPS), "-pix_fmt", "yuv420p", "-an", str(mp4)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return mp4


def render_short(title: str, day_label: str, scenes: List[Dict[str, Any]], narration: str, out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = out_dir / "narration.mp3"
    srt_path = out_dir / "captions.srt"
    video_path = out_dir / "short.mp4"

    words = _synthesize(narration, str(audio_path))
    _write_karaoke_srt(words, str(srt_path))

    audio_dur = words[-1]["end"] if words else 30.0
    total = min(max(audio_dur + 0.25, 12.0), 58.0)
    weights = [s.get("weight", 1.0) for s in scenes]
    wsum = sum(weights) or 1.0
    durations = [round(total * (s.get("weight", 1.0) / wsum), 2) for s in scenes]
    # fix rounding drift
    drift = round(total - sum(durations), 2)
    if durations:
        durations[-1] = round(durations[-1] + drift, 2)

    prepared = []
    for sc in scenes:
        prepared.append({
            "html": _scene_html(sc["kind"], sc.get("data", {})),
            "caption": sc.get("caption", ""),
            "_day": day_label,
            "_title": title,
        })

    raw_mp4 = _render_video(prepared, durations, out_dir, total)

    # ambient music bed (low drone) mixed under voiceover
    music_path = out_dir / "music.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "sine=frequency=110:duration=" + str(total),
        "-f", "lavfi", "-i", "sine=frequency=164.81:duration=" + str(total),
        "-f", "lavfi", "-i", "sine=frequency=220:duration=" + str(total),
        "-filter_complex", "[0][1][2]amix=inputs=3:duration=first,volume=0.035,afade=t=in:d=1.2,afade=t=out:st=" + str(total-1.5) + ":d=1.5",
        "-c:a", "libmp3lame", "-q:a", "5", str(music_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # final mix: video + voiceover + music, burn karaoke subs, pro encode
    vf = ("subtitles=" + str(srt_path).replace("\\", "/").replace(":", "\\:") +
          ":force_style='FontName=Arial,FontSize=11,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=470'")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_mp4),
        "-i", str(audio_path),
        "-i", str(music_path),
        "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:weights=1 0.35[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-r", str(FPS), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest", str(video_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)
    if proc.returncode != 0:
        # retry without subtitles filter (path issues)
        cmd2 = [
            "ffmpeg", "-y", "-i", str(raw_mp4), "-i", str(audio_path), "-i", str(music_path),
            "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:weights=1 0.35[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(video_path),
        ]
        subprocess.run(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # cleanup intermediates
    for f in (out_dir / "_raw").iterdir():
        f.unlink()
    (out_dir / "_raw").rmdir()
    for f in (out_dir / "raw.mp4", out_dir / "music.mp3"):
        try: f.unlink()
        except Exception: pass

    return {"video_path": str(video_path), "srt_path": str(srt_path), "audio_path": str(audio_path),
            "duration": round(total, 2), "scenes": len(scenes)}


DEMO_SCENES = [
    {"kind": "concept", "weight": 0.9, "caption": "An API is not a server",
     "data": {"pills": [{"label": "01 / hook", "color": "cyan"}],
              "body": "An API is a contract between two programs. It defines what you can ask for, and what you get back."}},
    {"kind": "flow", "weight": 1.2, "caption": "Request, response, repeat",
     "data": {"nodes": [{"text": "Your app", "cls": ""}, {"text": "Request", "cls": "accent"},
                        {"text": "Service", "cls": ""}, {"text": "Response", "cls": "accent"}]}},
    {"kind": "analogy", "weight": 1.1, "caption": "Think of a restaurant menu",
     "data": {"cards": [
         {"kicker": "Menu", "title": "The contract"},
         {"kicker": "Kitchen", "title": "The service"},
         {"kicker": "Waiter", "title": "Request and response"}]}},
    {"kind": "concept", "weight": 1.0, "caption": "A good contract sets expectations",
     "data": {"pills": [{"label": "Inputs", "color": "cyan"}, {"label": "Outputs", "color": "green"},
                         {"label": "Errors", "color": "red"}, {"label": "Limits", "color": "amber"}],
              "body": "A good API makes the contract explicit. Predictability is the feature."}},
    {"kind": "takeaway", "weight": 0.8, "caption": "That is why APIs matter",
     "data": {"text": "An API hides the kitchen and keeps the promise. That is the whole idea."}},
]

DEMO_NARRATION = (
    "An API is not a server. It is a contract between two programs. "
    "Your app sends a request, the service handles it, and returns a response. "
    "Think of a restaurant menu. The menu is the contract. The kitchen is the service. "
    "The waiter carries the request and response. You never walk into the kitchen. "
    "A good API defines inputs, outputs, errors, and limits. That predictability is the point. "
    "It hides the kitchen and keeps the promise. Follow for plain English tech."
)

def main():
    out = OUT_ROOT / "what_is_an_api_demo"
    if out.exists():
        shutil.rmtree(out)
    res = render_short("What Is an API?", "Plain English Tech", DEMO_SCENES, DEMO_NARRATION, out)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
