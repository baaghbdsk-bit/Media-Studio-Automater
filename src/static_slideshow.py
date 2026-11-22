"""Refined static slideshow renderer for 1080x1920 shorts.

Each beat is a timed, fully static card. HyperFrames shows/hides cards via
``data-start`` / ``data-duration``, so transitions are hard cuts with no motion.
Meaning is carried by a labeled CSS diagram, a content-specific headline, a
support line, and a detail strip of extracted metrics — no animation at all.

Public entry point::

    build_static_slideshow_html(topic, script, storyboard, duration) -> str
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List

RECIPES = (
    "flood", "queue", "parallel_grid", "race", "bottleneck", "merge", "payoff",
)

PALETTES = {
    "news": ("#fbbf24", "#f43f5e", "#f8fafc"),
    "concept": ("#38bdf8", "#34d399", "#f8fafc"),
    "deep": ("#a78bfa", "#22d3ee", "#f8fafc"),
}

_STAT_RE = re.compile(
    r"\b\d[\d,.]*\s*(?:%|x|times?|cores?|threads?|seconds?|minutes?|hours?|"
    r"days?|million|billion|trillion|models?|parameters?)\b",
    re.I,
)


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _num(value: Any, default: int, cap: int = 48) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = default
    return max(1, min(cap, n))


def _palette(storyboard: Dict[str, Any], topic: Dict[str, Any]) -> tuple:
    supplied = storyboard.get("palette") or {}
    key = "news" if str(topic.get("pillar") or "").upper() == "NEWS" else "concept"
    c1 = supplied.get("c1") or PALETTES[key][0]
    c2 = supplied.get("c2") or PALETTES[key][1]
    ink = supplied.get("ink") or "#f8fafc"
    return str(c1), str(c2), str(ink)


def _clamp_text(text: str, limit: int = 160) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _support(script_beat: Dict[str, Any], story_beat: Dict[str, Any]) -> str:
    lines = [str(x).strip() for x in (script_beat.get("lines") or []) if str(x).strip()]
    if lines:
        # The first line mirrors the focus headline — skip it to avoid
        # printing the same phrase twice on one slide.
        detail = lines[1:] or lines[:1]
        return _clamp_text(" ".join(detail[:2]), 170)
    return _clamp_text(story_beat.get("on_screen_text") or story_beat.get("visual_metaphor"), 170)


def _stat(script_beat: Dict[str, Any]) -> str:
    narration = " ".join(
        [str(script_beat.get("narration") or "")]
        + [str(x) for x in (script_beat.get("lines") or [])]
    )
    match = _STAT_RE.search(narration)
    return match.group(0).upper() if match else ""


def _tiles(count: int, cls: str, x: int, y: int, cols: int, w: int, h: int, gap: int = 12) -> str:
    out: List[str] = []
    for i in range(count):
        col, row = i % cols, i // cols
        opacity = 0.48 + (i % 4) * 0.15
        out.append(
            '<div class="tile %s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;opacity:%.2f"></div>'
            % (cls, x + col * (w + gap), y + row * (h + gap), w, h, opacity)
        )
    return "".join(out)


def _label(text: str, top: int = 10) -> str:
    return '<div class="diagram-label" style="top:%dpx">%s</div>' % (top, _esc(text))


def _legend(*items: str) -> str:
    return '<div class="legend">%s</div>' % "".join(
        '<span><i></i>%s</span>' % _esc(item) for item in items
    )


def _flood(params: Dict[str, Any]) -> str:
    n = _num(params.get("count"), 32, 48)
    return (
        _label("VOLUME · %d ITEMS POURING IN" % n)
        + _tiles(n, "tint", 40, 80, 8, 96, 62, 10)
        + _legend("INPUT", "PROCESS", "OVERFLOW")
    )


def _queue(params: Dict[str, Any]) -> str:
    n = _num(params.get("count"), 10, 16)
    gap = 8
    w = min(112, (860 - (n - 1) * gap) // n)
    return (
        _label("SEQUENCE · ONE AT A TIME")
        + '<div class="tag" style="left:0px;top:360px">CPU</div>'
        + _tiles(n, "", (930 - (n * (w + gap) - gap)) // 2, 350, n, w, 100, gap)
        + '<div class="tag right" style="right:0px;top:360px">SLOW</div>'
        + _legend("WAITING", "SERVED", "BLOCKED")
    )


def _parallel_grid(params: Dict[str, Any]) -> str:
    rows = _num(params.get("rows"), 3, 5)
    cols = _num(params.get("cols"), 4, 6)
    w, h, gap = 146, 146, 18
    total_w = cols * w + (cols - 1) * gap
    x0 = (960 - total_w) // 2
    return (
        _label("PARALLEL · %d WORKERS AT ONCE" % (rows * cols))
        + _tiles(rows * cols, "cyan", x0, 110, cols, w, h, gap)
        + _legend("CORE", "ACTIVE", "COMPLETE")
    )


def _race(params: Dict[str, Any]) -> str:
    labels = params.get("labels") or ["A", "B", "C"]
    if not isinstance(labels, list):
        labels = ["A", "B", "C"]
    labels = [str(x)[:8] for x in labels[:3]] or ["A", "B", "C"]
    widths = [82, 58, 38]
    out = [_label("RACE · FASTEST PATH WINS"), '<div class="finish">FINISH</div>']
    for i, label in enumerate(labels):
        out.append(
            '<div class="lane" style="top:%dpx"><span class="lane-label">%s</span>'
            '<div class="lane-bar" style="width:%d%%"></div>'
            '<span class="lane-pct">%d%%</span></div>'
            % (110 + i * 190, _esc(label), widths[i], widths[i])
        )
    return "".join(out) + _legend("WINNER", "ALTERNATIVE", "SLOWER")


def _bottleneck(params: Dict[str, Any]) -> str:
    cap = _num(params.get("capacity"), 5, 10)
    return (
        _label("BOTTLENECK · ONLY %d THROUGH THE GAP" % cap)
        + _tiles(12, "", 20, 130, 3, 104, 86, 14)
        + '<div class="funnel"><div class="funnel-top"></div><div class="funnel-neck"></div>'
        + '<div class="funnel-cap">%d/s</div></div>' % cap
        + _tiles(cap, "tint", 660, 230, 2, 104, 86, 14)
        + _legend("ARRIVING", "QUEUE", "THROUGHPUT")
    )


def _merge(params: Dict[str, Any]) -> str:
    n = _num(params.get("inputs"), 3, 4)
    out = [_label("MERGE · %d STREAMS BECOME ONE" % n)]
    for col in range(n):
        out.append(_tiles(6, "cyan", 10 + col * 200, 190, 1, 116, 74, 16))
        out.append(
            '<div class="stream-label" style="left:%dpx;top:735px">STREAM %d</div>'
            % (10 + col * 200, col + 1)
        )
    out.append('<div class="arrow">→</div>')
    out.append('<div class="chip">%s</div>' % _esc(params.get("label") or "ONE"))
    return "".join(out)


def _payoff(params: Dict[str, Any]) -> str:
    value = _clamp_text(params.get("value") or "RESULT", 10)
    label = _clamp_text(params.get("label") or "THE GAIN", 24)
    return (
        _label("PAYOFF · THE RESULT LANDS")
        + '<div class="source-chips">• • •</div>'
        + '<div class="payoff">%s</div>'
        + '<div class="payoff-label">%s</div>' % _esc(label)
        + _legend("INPUT", "PROCESS", "OUTCOME")
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
 radial-gradient(circle at 50% 26%,rgba(var(--c1rgb),.17) 0%,rgba(var(--c2rgb),.06) 46%,#070d18 84%)}
.rail{position:absolute;left:0;top:0;width:10px;height:100%;background:linear-gradient(180deg,var(--c1),var(--c2))}
.kicker{position:absolute;left:56px;top:52px;font-size:23px;font-weight:800;letter-spacing:.15em;
 text-transform:uppercase;color:var(--c1)}
.pillar{position:absolute;right:56px;top:52px;font-size:19px;font-weight:700;letter-spacing:.13em;color:#8fa3bf}
.rule-top{position:absolute;left:56px;right:56px;top:98px;height:2px;background:rgba(255,255,255,.14)}
.canvas{position:absolute;left:60px;top:150px;width:960px;height:860px}
.diagram-label{position:absolute;left:0;font-size:21px;font-weight:800;letter-spacing:.14em;
 text-transform:uppercase;color:var(--c2)}
.tile{position:absolute;border-radius:13px;background:#e6edf8;box-shadow:inset 0 -8px 0 rgba(0,0,0,.18)}
.tile.tint{background:var(--c1)}
.tile.cyan{background:var(--c2)}
.legend{position:absolute;left:0;bottom:6px;display:flex;gap:34px;font-size:18px;font-weight:700;
 letter-spacing:.1em;text-transform:uppercase;color:#8fa3bf}
.legend span{display:flex;align-items:center;gap:9px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:50%;background:var(--c1)}
.legend span:nth-child(2) i{background:var(--c2)}
.legend span:nth-child(3) i{background:#94a3b8}
.tag{position:absolute;font-size:20px;font-weight:900;letter-spacing:.1em;color:var(--c1)}
.tag.right{color:#f43f5e}
.lane{position:absolute;left:70px;width:820px;height:70px;display:flex;align-items:center;gap:18px}
.lane-label{width:44px;font-size:26px;font-weight:900;color:var(--c1)}
.lane-bar{height:52px;border-radius:999px;background:linear-gradient(90deg,var(--c1),var(--c2))}
.lane-pct{font-size:22px;font-weight:800;color:#dbe7f5}
.finish{position:absolute;right:20px;top:80px;height:620px;width:4px;background:rgba(255,255,255,.30)}
.funnel{position:absolute;left:380px;top:170px;width:220px;height:520px}
.funnel-top{width:100%;height:0;border-left:110px solid transparent;border-right:110px solid transparent;
 border-bottom:250px solid rgba(var(--c2rgb),.34)}
.funnel-neck{width:74px;height:208px;margin:0 auto;background:rgba(var(--c1rgb),.58);border-radius:0 0 18px 18px}
.funnel-cap{position:absolute;left:50%;top:490px;transform:translateX(-50%);font-size:22px;
 font-weight:900;color:var(--c1);white-space:nowrap}
.arrow{position:absolute;left:675px;top:360px;font-size:104px;font-weight:900;color:var(--c1)}
.chip{position:absolute;left:790px;top:350px;width:150px;height:150px;border-radius:30px;display:flex;
 align-items:center;justify-content:center;font-size:29px;font-weight:900;color:#07131f;background:var(--c2)}
.stream-label{position:absolute;font-size:17px;font-weight:800;letter-spacing:.08em;color:#8fa3bf}
.source-chips{position:absolute;left:300px;top:390px;font-size:52px;color:var(--c2);letter-spacing:.2em}
.payoff{position:absolute;left:230px;top:300px;width:600px;height:220px;border-radius:36px;display:flex;
 align-items:center;justify-content:center;font-size:104px;font-weight:900;letter-spacing:-.03em;
 color:#06131f;background:linear-gradient(135deg,var(--c1),var(--c2))}
.payoff-label{position:absolute;left:230px;top:545px;width:600px;text-align:center;font-size:26px;
 font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--c2)}
.detail-row{position:absolute;left:56px;right:56px;top:1010px;height:80px;display:flex;gap:18px}
.detail-chip{flex:1;border:1px solid rgba(var(--c2rgb),.35);border-radius:18px;background:rgba(11,20,35,.82);
 display:flex;flex-direction:column;justify-content:center;padding:0 24px}
.detail-chip .k{font-size:16px;font-weight:800;letter-spacing:.14em;color:#8fa3bf;text-transform:uppercase}
.detail-chip .v{margin-top:6px;font-size:30px;font-weight:900;color:var(--ink);white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis}
.copy{position:absolute;left:56px;right:56px;top:1120px;height:430px;padding:34px 38px;border-radius:30px;
 background:rgba(8,15,28,.72);border:1px solid rgba(var(--c1rgb),.24);box-shadow:0 24px 70px rgba(0,0,0,.4)}
.focus{font-size:88px;font-weight:900;line-height:1.02;letter-spacing:-.035em;color:var(--ink);
 text-transform:uppercase;text-shadow:0 10px 36px rgba(0,0,0,.5)}
.support{margin-top:28px;font-size:37px;font-weight:650;line-height:1.26;color:#cdd9ea}
.foot{position:absolute;left:56px;right:56px;bottom:74px;height:8px;background:rgba(255,255,255,.12);border-radius:9px}
.foot .fill{height:100%;border-radius:9px;background:linear-gradient(90deg,var(--c1),var(--c2))}
.count{position:absolute;right:56px;bottom:108px;font-size:21px;font-weight:800;letter-spacing:.12em;color:#8fa3bf}
.brand{position:absolute;left:56px;bottom:104px;font-size:18px;font-weight:700;letter-spacing:.1em;color:#8fa3bf}
"""


def _detail_chips(script_beat: Dict[str, Any], story_beat: Dict[str, Any], topic: Dict[str, Any]) -> str:
    stat = _stat(script_beat) or _clamp_text(
        story_beat.get("focus_label") or (story_beat.get("params") or {}).get("label") or "KEY IDEA", 18
    ).upper()
    key = _clamp_text(story_beat.get("on_screen_text") or story_beat.get("focus_label") or "INSIGHT", 20)
    pillar = _clamp_text(str(topic.get("pillar") or "CONCEPT"), 16).upper()
    return (
        '<div class="detail-chip"><span class="k">BY THE NUMBERS</span><span class="v">%s</span></div>'
        '<div class="detail-chip"><span class="k">THE IDEA</span><span class="v">%s</span></div>'
        '<div class="detail-chip"><span class="k">PILLAR</span><span class="v">%s</span></div>'
        % (_esc(stat), _esc(key), _esc(pillar))
    )


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

    def _rgb(value: str, fallback: str) -> str:
        if value.startswith("#") and len(value) == 7:
            try:
                return ",".join(str(int(value[i:i + 2], 16)) for i in (1, 3, 5))
            except ValueError:
                pass
        return fallback

    rgb1 = _rgb(c1, "56,189,248")
    rgb2 = _rgb(c2, "52,211,153")
    pillar = _esc(str(topic.get("pillar") or "CONCEPT").upper()[:18])

    slides: List[str] = []
    for index in range(count):
        script_beat = script_beats[index] if index < len(script_beats) else {}
        story_beat = story_beats[index] if index < len(story_beats) else {}
        recipe = str(story_beat.get("template_id") or RECIPES[index % len(RECIPES)])
        diagram = _DIAGRAMS.get(recipe, _flood)(story_beat.get("params") or {})
        focus = _clamp_text(story_beat.get("focus_label") or script_beat.get("focus_word") or "IDEA", 26)
        support = _support(script_beat, story_beat)
        label = _esc(str(script_beat.get("label") or "BEAT %d" % (index + 1))[:28])
        start = index * span
        width = ((index + 1) / count) * 100
        slides.append(
            '<div class="clip" data-start="%.3f" data-duration="%.3f" '
            'style="--c1:%s;--c2:%s;--ink:%s;--c1rgb:%s;--c2rgb:%s">'
            '<div class="rail"></div>'
            '<div class="kicker">%02d · %s</div><div class="pillar">%s</div>'
            '<div class="rule-top"></div>'
            '<div class="canvas">%s</div>'
            '<div class="detail-row">%s</div>'
            '<div class="copy"><div class="focus">%s</div><div class="support">%s</div></div>'
            '<div class="brand">NEUBENCH.WORKERS.DEV</div>'
            '<div class="foot"><div class="fill" style="width:%.2f%%"></div></div>'
            '<div class="count">%02d / %02d</div></div>'
            % (
                start, span, _esc(c1), _esc(c2), _esc(ink), rgb1, rgb2,
                index + 1, label, pillar, diagram,
                _detail_chips(script_beat, story_beat, topic),
                _esc(focus), _esc(support), width, index + 1, count,
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
