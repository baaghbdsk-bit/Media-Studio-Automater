"""Motion-rich, single-world 1080x1920 HyperFrames/GSAP short generator.

Replaces static multi-card slides with one continuous composition: a persistent
parallax world under a slow camera push, seven masked focus-word beats joined by
clip-path wipes, word-timed captions and an edge progress rail. All motion lives
on one paused timeline exposed as ``window.__timelines["main"]`` so HyperFrames
can seek deterministically to any frame.
"""

from __future__ import annotations

import html
import math
import re
from typing import Any, List

# Same CDN URL used by video_generator._build_vertical_short_html.
GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

BG = "#06080d"
INK = "#f4f6fb"

# Four colours, fixed meaning: background, ink, primary accent, contrast accent.
PALETTES = {
    "news": ("#fbbf24", "#f43f5e", "251, 191, 36", "244, 63, 94"),
    "concept": ("#22d3ee", "#34d399", "34, 211, 238", "52, 211, 153"),
    "comparison": ("#a78bfa", "#fbbf24", "167, 139, 250", "251, 191, 36"),
}

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--bg); overflow: hidden; }
body {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--ink);
}
#root { width: 1080px; height: 1920px; position: relative; overflow: hidden; background: var(--bg); }
#world { position: absolute; inset: 0; transform-origin: 50% 42%; }
.bg {
  position: absolute; inset: 0;
  background: radial-gradient(circle at 50% 40%, rgba(var(--c1rgb), 0.17) 0%, rgba(var(--c2rgb), 0.06) 38%, var(--bg) 78%);
}
.grid {
  position: absolute; inset: -240px;
  background-image:
    linear-gradient(rgba(var(--c1rgb), 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--c1rgb), 0.07) 1px, transparent 1px);
  background-size: 120px 120px;
}
.grid.b {
  background-image: radial-gradient(rgba(var(--c2rgb), 0.55) 2px, transparent 2px);
  background-size: 90px 90px; opacity: 0.5;
}
.halo {
  position: absolute; left: 50%; top: 42%; width: 1000px; height: 1000px;
  margin-left: -500px; margin-top: -500px; border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--c1rgb), 0.20) 0%, rgba(var(--c1rgb), 0) 68%);
}
.focal {
  position: absolute; left: 50%; top: 495px; width: 240px; height: 240px;
  margin-left: -120px; margin-top: -120px; border: 3px solid rgba(var(--c1rgb), 0.55);
  border-radius: 50%; opacity: 0.35;
}
.beat { position: absolute; inset: 0; clip-path: inset(0 100% 0 0); transform-origin: 50% 45%; z-index: 5; }
.label-mask, .focus-mask, .support-mask { position: absolute; left: 60px; width: 960px; overflow: hidden; }
.label-mask { top: 300px; height: 46px; }
.focus-mask { top: 410px; height: 180px; }
.support-mask { top: 630px; height: 130px; }
.label {
  display: flex; align-items: center; justify-content: center; height: 100%;
  font-size: 23px; font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase;
  text-align: center; color: var(--c1); opacity: 0; transform: translateX(-30px);
}
.focus {
  display: flex; align-items: center; justify-content: center; flex-wrap: wrap;
  height: 100%; text-align: center;
  font-weight: 900; line-height: 1.05; letter-spacing: -0.02em; color: var(--ink);
}
.chmask { display: inline-block; overflow: hidden; vertical-align: bottom; }
/* Opacity-only initial state: the masked offset is driven by GSAP yPercent so
   it never gets parsed as a leftover pixel `y` translation. */
.ch { display: inline-block; opacity: 0; }
.sp { display: inline-block; white-space: pre; }
.support {
  display: flex; align-items: center; justify-content: center; height: 100%;
  font-size: 38px; font-weight: 700; line-height: 1.25; text-align: center;
  color: var(--ink); opacity: 0; transform: translateY(40px);
}
.beat.alt .label, .beat.alt .focus { color: var(--c2); }
.cap {
  position: absolute; left: 60px; top: 900px; width: 960px; height: 450px;
  display: flex; flex-direction: column; justify-content: center; gap: 20px;
  z-index: 8; text-align: center;
}
.cap-line { font-size: 34px; font-weight: 700; line-height: 1.34; }
.w { color: var(--ink); opacity: 0.5; }
.progress-track {
  position: absolute; left: 0; top: 0; width: 1080px; height: 8px;
  background: rgba(255, 255, 255, 0.10); z-index: 20;
}
.progress-fill {
  width: 100%; height: 100%; background: var(--c1);
  transform: scaleX(0); transform-origin: left center;
}
"""


def _esc(value: Any) -> str:
    """HTML-escape user-authored script text before embedding it."""
    return html.escape(str(value), quote=True)


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce a possibly missing/string timestamp to a finite float."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _palette(topic: dict, script: dict) -> tuple:
    """Choose a pillar palette (NEWS / comparison / concept) deterministically."""
    pillar = str(topic.get("pillar") or topic.get("category") or "").lower()
    title = str(script.get("title") or topic.get("title") or "").lower()
    blob = pillar + " " + title
    if "news" in blob or "breaking" in blob or "headline" in blob:
        return PALETTES["news"]
    if (
        "compar" in blob
        or " versus " in blob
        or " vs " in blob
        or " vs." in blob
        or " vs:" in blob
        or " or " in title
    ):
        return PALETTES["comparison"]
    return PALETTES["concept"]


def _focus_markup(text: str) -> str:
    """Wrap each character in its own overflow-hidden mask for staggered reveals."""
    text = (text or "").strip() or "IDEA"
    chunks: List[str] = []
    for ch in text:
        if ch.isspace():
            chunks.append('<span class="sp"> </span>')
        else:
            chunks.append(
                '<span class="chmask"><span class="ch">' + _esc(ch) + "</span></span>"
            )
    return "".join(chunks)


def _support_text(beat: dict) -> str:
    """Pick one short supporting line from a beat's lines/narration fields."""
    lines = beat.get("lines")
    if isinstance(lines, (list, tuple)):
        candidates = [str(x).strip() for x in lines if str(x).strip()]
        text = candidates[0] if candidates else ""
    else:
        text = str(lines or "").strip()
    if not text:
        narration = str(beat.get("narration") or "").strip()
        parts = re.split(r"(?<=[.!?])\s+", narration)
        text = parts[0] if parts and parts[0] else "Follow the idea"
    if len(text) > 96:
        text = text[:93] + "..."
    return _esc(text)


def _resolve_words(words: list, script: dict, duration: float) -> List[dict]:
    """Use captured word timings, falling back to evenly spaced narration words."""
    out: List[dict] = []
    for item in words or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        start = min(max(_num(item.get("start")), 0.0), duration)
        end = min(max(_num(item.get("end"), start + 0.15), start + 0.08), duration)
        out.append({"text": text, "start": start, "end": end})
    if out:
        return out
    narration = str(script.get("narration") or "")
    tokens = narration.split()
    if not tokens:
        return out
    step = duration / len(tokens)
    for idx, token in enumerate(tokens):
        out.append(
            {
                "text": token,
                "start": idx * step,
                "end": min((idx + 1) * step, duration),
            }
        )
    return out


def _caption_lines(items: List[dict]) -> List[List[dict]]:
    """Split timed words across at most two visually centered caption lines."""
    total = sum(len(w["text"]) + 1 for w in items)
    capacity = max(24, min(46, int(math.ceil(total / 2.0)) + 3))
    lines: List[List[dict]] = [[]]
    used = 0
    for item in items:
        cost = len(item["text"]) + 1
        if used + cost > capacity and lines[-1]:
            lines.append([])
            used = 0
        lines[-1].append(item)
        used += cost
    if len(lines) > 2:
        lines = [lines[0], [word for line in lines[1:] for word in line]]
    return lines


def _beat_starts(beats: List[dict], duration: float) -> List[float]:
    """Sanitize target_s values into monotonic, in-range beat start times."""
    count = len(beats)
    gap = duration / max(count, 1) * 0.55
    fallback = [duration * i / max(count, 1) for i in range(count)]
    starts: List[float] = []
    for index, beat in enumerate(beats):
        raw = _num(beat.get("target_s"), -1.0)
        if raw < 0 or raw >= duration or (starts and raw <= starts[-1] + gap):
            raw = fallback[index]
        starts.append(raw)
    starts[0] = 0.0
    for index in range(1, count):
        floor = starts[index - 1] + gap
        if starts[index] < floor:
            starts[index] = min(floor, duration - gap)
    starts[-1] = min(starts[-1], max(0.0, duration - gap))
    return starts


def build_short_html(topic: dict, script: dict, words: list, duration: float) -> str:
    """Return a complete, self-contained HyperFrames HTML document string.

    Args:
        topic: topic dict; ``pillar``/``category`` selects the colour palette.
        script: output of ``short_script.build_short_script`` (title, beats, ...).
        words: ``[{"text", "start", "end"}]`` word timings from ``voice``.
        duration: final narration duration in seconds.
    """
    topic = topic or {}
    script = script or {}
    total = max(0.5, _num(duration, 1.0))
    dstr = f"{total:.1f}"

    accent, contrast, accent_rgb, contrast_rgb = _palette(topic, script)
    title = _esc(script.get("title") or topic.get("title") or "Short")

    beats: List[dict] = list(script.get("beats") or [])
    if not beats:
        beats = [
            {
                "label": f"BEAT {idx + 1:02d}",
                "focus_word": "IDEA",
                "lines": ["Follow the idea"],
                "target_s": total * idx / 7.0,
            }
            for idx in range(7)
        ]
    starts = _beat_starts(beats, total)
    ends = [starts[i + 1] if i + 1 < len(beats) else total for i in range(len(beats))]

    timed_words = _resolve_words(words, script, total)
    caption_rows = _caption_lines(timed_words)

    # --- HTML world -------------------------------------------------------
    body: List[str] = []
    body.append(
        '<div id="root" data-composition-id="main" data-start="0" '
        f'data-duration="{dstr}" data-width="1080" data-height="1920">'
    )
    body.append(
        '<audio id="narration" src="narration_master.wav" data-start="0" '
        f'data-duration="{dstr}" data-volume="1"></audio>'
    )
    body.append('<div id="world">')
    body.append('<div class="bg"></div>')
    body.append('<div class="grid" id="grid1"></div>')
    body.append('<div class="grid b" id="grid2"></div>')
    body.append('<div class="halo" id="halo"></div>')
    body.append('<div class="focal" id="focal"></div>')
    body.append('<div class="dots" id="dots"></div>')

    for index, beat in enumerate(beats):
        focus = str(beat.get("focus_word") or "").strip() or "IDEA"
        focus_size = (
            120
            if len(focus) <= 5
            else 110
            if len(focus) <= 8
            else 98
            if len(focus) <= 12
            else 88
            if len(focus) <= 18
            else 84
        )
        label = _esc(beat.get("label") or f"BEAT {index + 1:02d}")
        alt = " alt" if index % 2 else ""
        body.append(
            f'<div id="beat{index}" class="beat clip{alt}" '
            f'data-start="{starts[index]:.1f}" '
            f'data-duration="{max(0.0, ends[index] - starts[index]):.1f}" '
            'data-track-index="0">'
        )
        body.append(f'<div class="label-mask"><div class="label" id="label{index}">{label}</div></div>')
        body.append(
            f'<div class="focus-mask"><div class="focus" id="focus{index}" '
            f'style="font-size:{focus_size}px">{_focus_markup(focus)}</div></div>'
        )
        body.append(
            f'<div class="support-mask"><div class="support" id="support{index}">'
            f'{_support_text(beat)}</div></div>'
        )
        body.append("</div>")

    body.append('<div class="cap" id="captions">')
    word_id = 0
    for row in caption_rows:
        body.append('<div class="cap-line">')
        for item in row:
            body.append(f'<span class="w" id="w{word_id}">{_esc(item["text"])}</span> ')
            word_id += 1
        body.append("</div>")
    body.append("</div>")
    body.append("</div>")  # /world
    body.append('<div class="progress-track"><div class="progress-fill" id="progress"></div></div>')
    body.append("</div>")  # /root

    # --- Deterministic paused timeline ------------------------------------
    # Every tween uses an explicit absolute position and fromTo(); no time-,
    # random- or network-dependent values are ever read by the composition.
    js: List[str] = [
        "window.__timelines = window.__timelines || {};",
        "const tl = gsap.timeline({paused:true});",
        'window.__timelines["main"] = tl;',
    ]

    def add(selector: str, from_vars: str, to_vars: str, at: float) -> None:
        from_block = "{" + from_vars + "}"
        to_block = "{" + to_vars + ", immediateRender:false}"
        js.append(
            f'tl.fromTo("{selector}", {from_block}, {to_block}, {at:.3f});'
        )

    # Persistent world motion.
    add("#world", "scale:1", f'scale:1.06, duration:{total:.3f}, ease:"none"', 0)
    add("#dots", "x:0, y:0", f'x:-90, y:-180, duration:{total:.3f}, ease:"none"', 0)
    add("#grid1", "y:0", f'y:-120, duration:{total:.3f}, ease:"none"', 0)
    add("#grid2", "x:0", f'x:120, duration:{total:.3f}, ease:"none"', 0)
    add(
        "#halo",
        "scale:0.9, opacity:0.55",
        f'scale:1.2, opacity:0.85, duration:{total:.3f}, ease:"none"',
        0,
    )
    # Focal ring returns to the exact frame-0 state at the end (loop rhyme).
    add(
        "#focal",
        "opacity:0.35, scale:1",
        f'opacity:0.12, scale:1.25, duration:{total / 2:.3f}, ease:"sine.inOut"',
        0,
    )
    add(
        "#focal",
        "opacity:0.12, scale:1.25",
        f'opacity:0.35, scale:1, duration:{total / 2:.3f}, ease:"sine.inOut"',
        total / 2,
    )
    add("#progress", "scaleX:0", f'scaleX:1, duration:{total:.3f}, ease:"none"', 0)

    # Beat entries (clip wipes + zoom punch) and faster exits.
    for index in range(len(beats)):
        start, end = starts[index], ends[index]
        span = max(0.6, end - start)
        in_dur = min(0.6, span * 0.28)
        out_dur = min(0.28, span * 0.14)
        exit_at = max(start + in_dur + 0.1, end - out_dur)
        focus_sel = f"#focus{index} .ch"

        add(
            f"#beat{index}",
            'clipPath:"inset(0 100% 0 0)", opacity:1',
            f'clipPath:"inset(0 0% 0 0)", duration:{in_dur:.3f}, ease:"power3.out"',
            start,
        )
        add(
            f"#beat{index}",
            "scale:1",
            f'scale:1.06, duration:{in_dur:.3f}, ease:"power2.out"',
            start,
        )
        add(
            f"#label{index}",
            "x:-30, opacity:0",
            f'x:0, opacity:1, duration:{in_dur * 0.8:.3f}',
            start + 0.04,
        )
        add(
            focus_sel,
            "yPercent:115, opacity:0",
            f'yPercent:0, opacity:1, duration:{in_dur:.3f}, stagger:0.035, ease:"power3.out"',
            start + 0.10,
        )
        add(
            f"#support{index}",
            "y:40, opacity:0",
            f'y:0, opacity:1, duration:{in_dur * 0.9:.3f}, ease:"power3.out"',
            start + 0.18,
        )

        add(
            f"#beat{index}",
            'clipPath:"inset(0 0% 0 0)"',
            f'clipPath:"inset(0 0 0 100%)", duration:{out_dur:.3f}, ease:"power2.in"',
            exit_at,
        )
        add(
            f"#beat{index}",
            "scale:1.06",
            f'scale:1.0, duration:{out_dur:.3f}, ease:"power2.in"',
            exit_at,
        )
        add(
            f"#label{index}",
            "x:0, opacity:1",
            f'x:30, opacity:0, duration:{out_dur:.3f}',
            exit_at,
        )
        add(
            focus_sel,
            "yPercent:0, opacity:1",
            f'yPercent:-115, opacity:0, duration:{out_dur:.3f}, stagger:0.018, ease:"power2.in"',
            exit_at,
        )
        add(
            f"#support{index}",
            "y:0, opacity:1",
            f'y:-30, opacity:0, duration:{out_dur:.3f}',
            exit_at,
        )

    # Word-level caption highlighting exactly on each spoken start/end.
    for index, item in enumerate(timed_words):
        start = min(max(item["start"], 0.0), total)
        end = min(max(item["end"], start + 0.08), total)
        selector = f"#w{index}"
        add(
            selector,
            f'color:"{INK}", opacity:0.5',
            f'color:"{accent}", opacity:1, duration:0.10',
            start,
        )
        add(
            selector,
            f'color:"{accent}", opacity:1',
            f'color:"{INK}", opacity:0.5, duration:0.16',
            end,
        )

    variables = (
        ":root{--bg:" + BG + ";--ink:" + INK
        + ";--c1:" + accent + ";--c2:" + contrast
        + ";--c1rgb:" + accent_rgb + ";--c2rgb:" + contrast_rgb + ";}\n"
    )
    dots_css = (
        ".dots{position:absolute;inset:-160px;opacity:0.30;"
        "background-image:radial-gradient(rgba(var(--c2rgb),0.55) 2px, transparent 2px);"
        "background-size:90px 90px;}\n"
    )

    document = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8" />',
        f"<title>{title} • Vertical Short</title>",
        f'<script src="{GSAP_CDN}"></script>',
        "<style>",
        variables + CSS + dots_css,
        "</style>",
        "</head>",
        "<body>",
        "\n".join(body),
        "<script>",
        "\n".join(js),
        "</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(document)
