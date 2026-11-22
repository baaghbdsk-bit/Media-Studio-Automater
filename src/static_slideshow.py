"""Refined static slideshow renderer for 1080x1920 shorts.

Each beat is a timed, fully static card. HyperFrames shows/hides cards via
``data-start`` / ``data-duration``, so transitions are hard cuts with no motion.
Meaning is carried by a content-specific headline plus a deterministic CSS
diagram chosen from the storyboard recipe vocabulary (flood, queue,
parallel_grid, race, bottleneck, merge, payoff).

Public entry point::

    build_static_slideshow_html(topic, script, storyboard, duration) -> str
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

RECIPES = (
    "flood", "queue", "parallel_grid", "race", "bottleneck", "merge", "payoff",
)

PALETTES = {
    "news": ("#fbbf24", "#f43f5e", "#f8fafc"),
    "concept": ("#38bdf8", "#34d399", "#f8fafc"),
    "deep": ("#a78bfa", "#22d3ee", "#f8fafc"),
}


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _num(value: Any, default: int, cap: int = 40) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = default
    return max(1, min(cap, n))


def _palette(storyboard: Dict[str, Any], topic: Dict[str, Any]) -> tuple:
    supplied = storyboard.get("palette") or {}
    c1 = supplied.get("c1") or PALETTES["news" if str(topic.get("pillar") or "").upper() == "NEWS" else "concept"][0]
    c2 = supplied.get("c2") or PALETTES["concept"][1]
    ink = supplied.get("ink") or "#f8fafc"
    return str(c1), str(c2), str(ink)


def _clamp_text(text: str, limit: int = 110) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _support(script_beat: Dict[str, Any], story_beat: Dict[str, Any]) -> str:
    lines = [str(x).strip() for x in (script_beat.get("lines") or []) if str(x).strip()]
    if lines:
        return _clamp_text(lines[0], 155)
    return _clamp_text(story_beat.get("on_screen_text") or story_beat.get("visual_metaphor"), 155)


def _tiles(count: int, cls: str, x: int, y: int, cols: int, w: int, h: int, gap: int = 12) -> str:
    out: List[str] = []
    for i in range(count):
        col, row = i % cols, i // cols
        opacity = 0.45 + (i % 4) * 0.16
        out.append(
            '<div class="tile %s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;opacity:%.2f"></div>'
            % (cls, x + col * (w + gap), y + row * (h + gap), w, h, opacity)
        )
    return "".join(out)


def _flood(params: Dict[str, Any]) -> str:
    n = _num(params.get("count"), 32, 48)
    return _tiles(n, "tint", 40, 30, 8, 96, 66, 10)


def _queue(params: Dict[str, Any]) -> str:
    n = _num(params.get("count"), 10, 16)
    gap = 8
    w = min(120, (880 - (n - 1) * gap) // n)
    return _tiles(n, "", (940 - (n * (w + gap) - gap)) // 2, 350, n, w, 110, gap)


def _parallel_grid(params: Dict[str, Any]) -> str:
    rows = _num(params.get("rows"), 3, 5)
    cols = _num(params.get("cols"), 4, 6)
    w, h, gap = 150, 150, 18
    total_w = cols * w + (cols - 1) * gap
    x0 = (960 - total_w) // 2
    return _tiles(rows * cols, "cyan", x0, 140, cols, w, h, gap)


def _race(params: Dict[str, Any]) -> str:
    labels = params.get("labels") or ["A", "B", "C"]
    if not isinstance(labels, list):
        labels = ["A", "B", "C"]
    labels = [str(x)[:8] for x in labels[:3]] or ["A", "B", "C"]
    widths = [82, 58, 38]
    out = ['<div class="finish">FINISH</div>']
    for i, label in enumerate(labels):
        out.append(
            '<div class="lane" style="top:%dpx"><span class="lane-label">%s</span>'
            '<div class="lane-bar" style="width:%d%%"></div></div>'
            % (110 + i * 190, _esc(label), widths[i])
        )
    return "".join(out)


def _bottleneck(params: Dict[str, Any]) -> str:
    left = _tiles(12, "", 20, 120, 3, 110, 90, 14)
    right = _tiles(_num(params.get("capacity"), 4, 8), "tint", 660, 220, 2, 110, 90, 14)
    return (
        left
        + '<div class="funnel"><div class="funnel-top"></div><div class="funnel-neck"></div></div>'
        + right
    )


def _merge(params: Dict[str, Any]) -> str:
    n = _num(params.get("inputs"), 3, 4)
    out: List[str] = []
    for col in range(n):
        out.append(_tiles(6, "cyan", 20 + col * 210, 180, 1, 120, 80, 16))
    out.append('<div class="arrow">→</div>')
    out.append('<div class="chip">%s</div>' % _esc(params.get("label") or "ONE"))
    return "".join(out)


def _payoff(params: Dict[str, Any]) -> str:
    value = _clamp_text(params.get("value") or "RESULT", 12)
    return (
        '<div class="source-chips">%s</div>'
        '<div class="payoff">%s</div>' % (
            "".join('<span class="src">•</span>' for _ in range(3)),
            _esc(value),
        )
    )


_DIAGRAMS = {
    "flood": _flood,
    "queue": _queue,
    "parallel_grid": _parallel_grid,
    "race": _race,
    "bottleneck": _bottleneck,
    "merge": _merge,
    "payoff": _payoff,
}

_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:#070d18;overflow:hidden}
body{font-family:"Inter","Segoe UI",Arial,sans-serif;color:var(--ink)}
.clip{position:absolute;inset:0;width:1080px;height:1920px;overflow:hidden;background:
 radial-gradient(circle at 50% 30%,rgba(var(--c1rgb),.16) 0%,rgba(var(--c2rgb),.06) 45%,#070d18 82%)}
.rule-top{position:absolute;left:60px;right:60px;top:96px;height:2px;background:rgba(255,255,255,.14)}
.kicker{position:absolute;left:60px;top:56px;font-size:24px;font-weight:800;letter-spacing:.16em;
 text-transform:uppercase;color:var(--c1)}
.pillar{position:absolute;right:60px;top:56px;font-size:20px;font-weight:700;letter-spacing:.14em;
 color:#8fa3bf}
.canvas{position:absolute;left:60px;top:170px;width:960px;height:900px}
.tile{position:absolute;border-radius:14px;background:#e6edf8;box-shadow:inset 0 -8px 0 rgba(0,0,0,.18)}
.tile.tint{background:var(--c1)}
.tile.cyan{background:var(--c2)}
.lane{position:absolute;left:70px;width:820px;height:70px;display:flex;align-items:center;gap:18px}
.lane-label{width:40px;font-size:26px;font-weight:900;color:var(--c1)}
.lane-bar{height:54px;border-radius:999px;background:linear-gradient(90deg,var(--c1),var(--c2))}
.finish{position:absolute;right:20px;top:60px;height:640px;width:4px;background:rgba(255,255,255,.32)}
.funnel{position:absolute;left:380px;top:170px;width:220px;height:520px}
.funnel-top{width:100%;height:0;border-left:110px solid transparent;border-right:110px solid transparent;
 border-bottom:260px solid rgba(var(--c2rgb),.32)}
.funnel-neck{width:74px;height:220px;margin:0 auto;background:rgba(var(--c1rgb),.55);border-radius:0 0 18px 18px}
.arrow{position:absolute;left:680px;top:390px;font-size:110px;font-weight:900;color:var(--c1)}
.chip{position:absolute;left:790px;top:360px;width:150px;height:150px;border-radius:32px;display:flex;
 align-items:center;justify-content:center;font-size:30px;font-weight:900;color:#07131f;background:var(--c2)}
.source-chips{position:absolute;left:250px;top:400px;font-size:58px;color:var(--c2);letter-spacing:.28em}
.payoff{position:absolute;left:230px;top:340px;width:600px;height:240px;border-radius:36px;display:flex;
 align-items:center;justify-content:center;font-size:110px;font-weight:900;letter-spacing:-.03em;
 color:#06131f;background:linear-gradient(135deg,var(--c1),var(--c2))}
.copy{position:absolute;left:60px;right:60px;top:1130px;height:520px}
.focus{font-size:96px;font-weight:900;line-height:1.02;letter-spacing:-.035em;color:var(--ink);
 text-transform:uppercase;text-shadow:0 12px 42px rgba(0,0,0,.55)}
.support{margin-top:36px;font-size:38px;font-weight:650;line-height:1.26;color:#cdd9ea;max-width:940px}
.foot{position:absolute;left:60px;right:60px;bottom:70px;height:8px;background:rgba(255,255,255,.12);border-radius:9px}
.foot .fill{height:100%;border-radius:9px;background:linear-gradient(90deg,var(--c1),var(--c2))}
.count{position:absolute;right:60px;bottom:104px;font-size:22px;font-weight:800;letter-spacing:.12em;color:#8fa3bf}
"""


def build_static_slideshow_html(
    topic: Dict[str, Any],
    script: Dict[str, Any],
    storyboard: Dict[str, Any],
    duration: float,
) -> str:
    """Return a complete static HyperFrames composition with hard-cut slides."""
    script_beats = [b for b in (script.get("beats") or []) if isinstance(b, dict)]
    story_beats = [b for b in (storyboard.get("beats") or []) if isinstance(b, dict)]
    count = max(len(script_beats), len(story_beats), 1)
    span = duration / count
    c1, c2, ink = _palette(storyboard, topic)
    rgb1 = ",".join(str(int(c1.lstrip("#")[i:i + 2], 16)) for i in (0, 2, 4)) if c1.startswith("#") else "56,189,248"
    rgb2 = ",".join(str(int(c2.lstrip("#")[i:i + 2], 16)) for i in (0, 2, 4)) if c2.startswith("#") else "52,211,153"
    pillar = _esc(str(topic.get("pillar") or "CONCEPT").upper()[:18])

    slides: List[str] = []
    for index in range(count):
        script_beat = script_beats[index] if index < len(script_beats) else {}
        story_beat = story_beats[index] if index < len(story_beats) else {}
        recipe = str(story_beat.get("template_id") or RECIPES[index % len(RECIPES)])
        diagram_fn = _DIAGRAMS.get(recipe, _flood)
        diagram = diagram_fn(story_beat.get("params") or {})
        focus = _clamp_text(story_beat.get("focus_label") or script_beat.get("focus_word") or "IDEA", 26)
        support = _support(script_beat, story_beat)
        label = _esc(str(script_beat.get("label") or "BEAT %d" % (index + 1))[:28])
        start = index * span
        width = ((index + 1) / count) * 100
        slides.append(
            '<div class="clip" data-start="%.3f" data-duration="%.3f" '
            'style="--c1:%s;--c2:%s;--ink:%s;--c1rgb:%s;--c2rgb:%s">'
            '<div class="kicker">%02d · %s</div><div class="pillar">%s</div>'
            '<div class="rule-top"></div>'
            '<div class="canvas">%s</div>'
            '<div class="copy"><div class="focus">%s</div><div class="support">%s</div></div>'
            '<div class="foot"><div class="fill" style="width:%.2f%%"></div></div>'
            '<div class="count">%02d / %02d</div></div>'
            % (
                start, span, _esc(c1), _esc(c2), _esc(ink), rgb1, rgb2,
                index + 1, label, pillar, diagram, _esc(focus), _esc(support),
                width, index + 1, count,
            )
        )

    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>'
        '<title>Static Slideshow Short</title><style>' + _CSS + '</style></head><body>'
        '<div id="root" data-composition-id="main" data-start="0" data-duration="%.3f" '
        'data-width="1080" data-height="1920">'
        '<audio id="narration" src="narration_master.wav" data-start="0" '
        'data-duration="%.3f" data-volume="1"></audio>'
        '%s</div></body></html>'
        % (duration, duration, "".join(slides))
    )
