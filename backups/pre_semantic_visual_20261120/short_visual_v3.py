"""Object-animation explainer for 1080x1920 HyperFrames shorts (v3).

This generator replaces the text-card motion of ``short_visual_v2`` with a
single, continuous world where *meaning is carried by shapes acting*, not by
words. Seven storyboard recipes (flood, queue, parallel_grid, race,
bottleneck, merge, payoff) render a reusable vocabulary of tiles, workers,
grids, bars, a bottleneck and a final chip/mosaic. Every recipe keeps its
objects moving for the full beat via explicit, finite idle cycles, so no
element is ever static for more than ~0.7s.

On top of that moving world, every beat renders a LARGE inline-SVG icon (chef
hat, cupcake, CPU, grid, clock, bolt, check, queue or funnel) as the focal
subject, plus a short, readable lower-third statement of what is happening.
The icon is chosen by the storyboard's ``icon`` field and literally depicts the
noun/metaphor of that beat's narration.

Everything is deterministic: one paused GSAP timeline exposed at
``window.__timelines["main"]``, every tween is an absolute-time ``fromTo`` and
nothing reads the clock, randomness or the network. Only transforms, opacity,
colour and beat-transition clip-paths are animated.

Public entry point::

    build_short_html_v3(topic, script, storyboard, words, duration) -> str
"""

from __future__ import annotations

import html
import math
import re
from typing import Any, Dict, List, Tuple

# Exactly the tag used by video_generator._build_vertical_short_html.
GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

# Fallback semantic palette (worker amber, grid cyan, payoff green).
_DEFAULT = {
    "bg": "#06080d",
    "ink": "#f4f6fb",
    "c1": "#fbbf24",
    "c2": "#22d3ee",
    "c3": "#34d399",
}

_RECIPES: Tuple[str, ...] = (
    "flood", "queue", "parallel_grid", "race", "bottleneck", "merge", "payoff",
)
_ALIASES = {
    "grid": "parallel_grid", "parallel": "parallel_grid", "workers": "parallel_grid",
    "flooding": "flood", "overwhelm": "flood", "tsunami": "flood",
    "line": "queue", "serial": "queue", "single": "queue",
    "versus": "race", "comparison": "race", "split": "race",
    "narrow": "bottleneck", "jam": "bottleneck", "funnel": "bottleneck",
    "combine": "merge", "join": "merge", "fusion": "merge",
    "final": "payoff", "result": "payoff", "reveal": "payoff",
}


# --------------------------------------------------------------------------- #
# Inline SVG icon library (self-contained: no external files, no network).
# Each icon uses a 48x48 viewBox and currentColor strokes, then the renderer
# scales it to ~300px via CSS transforms. "none" is not a shape: beats that
# request it fall back to the recipe's default icon so every beat has a focal
# subject.
# --------------------------------------------------------------------------- #
_ICON_TONE = {
    "chef": 1, "cupcake": 1, "bolt": 1,
    "clock": 2, "queue": 2, "funnel": 2, "cpu": 2, "grid": 2,
    "check": 3,
}

_ICON_BY_TEMPLATE = {
    "flood": "cupcake", "queue": "chef", "parallel_grid": "grid",
    "race": "bolt", "bottleneck": "funnel", "merge": "cpu", "payoff": "check",
}

_GRID_SQUARES = "".join(
    '<rect x="%d" y="%d" width="10" height="10" rx="2"%s/>'
    % (
        7 + c * 12, 7 + r * 12,
        ' fill="currentColor" stroke="none"' if (r + c) % 3 == 0 else "",
    )
    for r in range(3)
    for c in range(3)
)

_ICON_SVGS = {
    "chef": (
        '<path d="M13 24c-5 0-8.5-3.5-8.5-8 0-4.2 3.3-7.6 7.5-7.7'
        'C13.5 4.4 18 2 24 2s10.5 2.4 12 6.3c4.2.1 7.5 3.5 7.5 7.7'
        ' 0 4.5-3.5 8-8.5 8H13z"/>'
        '<path d="M13.5 11v7M24 8.5v9M34.5 11v7" opacity="0.55"/>'
        '<path d="M13 24h22v11H13z"/><path d="M13 29h22"/>'
        '<path d="M10.5 35h27v7h-27z"/><path d="M16 42h16"/>'
    ),
    "cupcake": (
        '<path d="M10 25h28l-4 17H14l-4-17z"/>'
        '<path d="M13.5 31h21M15 36h18M16.5 40h15"/>'
        '<path d="M9 25c-1.5-5 2.5-9 7.5-8-1-5 3-9 8-8'
        ' 3.5-3.5 9-2.5 11 2 4.5-.5 8 3 6 7.5-1 2-3 3.5-5.5 3.5H9z"/>'
        '<circle cx="24" cy="7" r="2.6" fill="currentColor" stroke="none"/>'
    ),
    "cpu": (
        '<rect x="10" y="10" width="28" height="28" rx="4"/>'
        '<rect x="17" y="17" width="14" height="14" rx="2"/>'
        '<circle cx="24" cy="24" r="2.4" fill="currentColor" stroke="none"/>'
        '<path d="M16 10V5M24 10V5M32 10V5M16 38v5M24 38v5M32 38v5'
        'M10 16H5M10 24H5M10 32H5M38 16h5M38 24h5M38 32h5"/>'
    ),
    "grid": _GRID_SQUARES,
    "clock": (
        '<circle cx="24" cy="24" r="18"/><path d="M24 12v12l8 5"/>'
        '<path d="M24 3v5M24 40v5M3 24h5M40 24h5"/>'
        '<circle cx="24" cy="24" r="2" fill="currentColor" stroke="none"/>'
    ),
    "bolt": (
        '<path d="M27.5 3 11 27h11l-2.5 18L38 20H26l1.5-17z"'
        ' fill="currentColor" stroke="none"/>'
        '<path d="M24 9 16 24h7l-2 11 10-14h-7l1-12z" fill="none"'
        ' stroke="#ffffff" stroke-opacity="0.5" stroke-width="1.4"/>'
    ),
    "check": (
        '<circle cx="24" cy="24" r="18"/>'
        '<path d="m14 25 7 7 14-16" stroke-width="4"/>'
    ),
    "queue": (
        '<circle cx="11" cy="14" r="4"/>'
        '<path d="M4 30c0-4.4 3.1-7.5 7-7.5s7 3.1 7 7.5"/>'
        '<circle cx="24" cy="14" r="4"/>'
        '<path d="M17 30c0-4.4 3.1-7.5 7-7.5s7 3.1 7 7.5"/>'
        '<circle cx="37" cy="14" r="4"/>'
        '<path d="M30 30c0-4.4 3.1-7.5 7-7.5s7 3.1 7 7.5"/>'
        '<path d="M4 39h40"/>'
    ),
    "funnel": (
        '<path d="M5 6h38L29.5 25v14l-11 5V25L5 6z"/>'
        '<path d="M9 13h30"/>'
        '<circle cx="24" cy="40" r="1.6" fill="currentColor" stroke="none"/>'
    ),
}


def _hero_svg(name: str) -> str:
    """Return a single self-contained, scalable SVG for an icon name."""
    return (
        '<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" '
        'fill="none" stroke="currentColor" stroke-width="2.4" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        "%s</svg>" % _ICON_SVGS[name]
    )


def _icon(beat: Dict[str, Any], index: int, template: str) -> str:
    """Resolve the storyboard icon, falling back to the recipe's literal noun."""
    raw = str(beat.get("icon") or "").strip().lower()
    if raw in _ICON_SVGS:
        return raw
    return _ICON_BY_TEMPLATE.get(template, "cpu")


_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--bg); overflow: hidden; }
body { font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--ink); }
#root { width: 1080px; height: 1920px; position: relative; overflow: hidden; background: var(--bg); }
.bg-canvas { position: absolute; inset: 0; background: radial-gradient(circle at 50% 38%, rgba(var(--c2rgb),0.16) 0%, rgba(var(--c1rgb),0.06) 42%, var(--bg) 80%); }
.grid-bg { position: absolute; inset: -300px; background-image: linear-gradient(rgba(var(--c2rgb),0.16) 2px, transparent 2px), linear-gradient(90deg, rgba(var(--c2rgb),0.16) 2px, transparent 2px); background-size: 64px 64px; opacity: 0.5; }
.world { position: absolute; inset: 0; transform-origin: 50% 45%; z-index: 2; }
.orb { position: absolute; border-radius: 50%; opacity: 0.28; z-index: 1; }
.orb.a { width: 560px; height: 560px; background: radial-gradient(circle, var(--c1) 0%, transparent 68%); }
.orb.b { width: 460px; height: 460px; background: radial-gradient(circle, var(--c2) 0%, transparent 68%); }
.orb.c { width: 400px; height: 400px; background: radial-gradient(circle, var(--c3) 0%, transparent 68%); }
.sweep { position: absolute; top: -20%; left: 0; width: 34%; height: 140%; z-index: 4; opacity: 0.13; transform: skewX(-18deg); background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.55) 45%, rgba(255,255,255,0.85) 52%, transparent 100%); }
.beat { position: absolute; inset: 0; clip-path: inset(0 100% 0 0); transform-origin: 50% 44%; z-index: 5; }
.cam { position: absolute; inset: 0; transform-origin: 50% 44%; }
.tile { position: absolute; border-radius: 13px; background: linear-gradient(145deg, #ffffff 0%, #cdd6e4 100%); box-shadow: inset 0 -7px 0 rgba(0,0,0,0.16), inset 0 3px 0 rgba(255,255,255,0.85); opacity: 0; }
.tile.tinted { background: linear-gradient(145deg, var(--c1) 0%, #9a5a06 100%); }
.tile.cyan { background: linear-gradient(145deg, var(--c2) 0%, #0e5f73 100%); }
.worker { position: absolute; border-radius: 40px; background: linear-gradient(150deg, var(--c1) 0%, rgba(0,0,0,0.34) 130%); box-shadow: inset 0 -10px 0 rgba(0,0,0,0.22), inset 0 4px 0 rgba(255,255,255,0.38); opacity: 0; }
.worker .eye { position: absolute; width: 16px; height: 20px; border-radius: 50%; background: rgba(0,0,0,0.72); top: 36%; }
.worker .eye.l { left: 29%; }
.worker .eye.r { right: 29%; }
.worker .mouth { position: absolute; left: 38%; right: 38%; height: 8px; border-radius: 8px; background: rgba(0,0,0,0.72); top: 64%; }
.worker .gear { position: absolute; left: 50%; top: 50%; width: 78%; height: 78%; margin-left: -39%; margin-top: -39%; border: 6px dashed rgba(255,255,255,0.32); border-radius: 50%; transform-origin: 50% 50%; }
.mini { position: absolute; border-radius: 9px; background-color: var(--c2); box-shadow: inset 0 -6px 0 rgba(0,0,0,0.25), inset 0 3px 0 rgba(255,255,255,0.30); opacity: 0; }
.mini::after { content: ""; position: absolute; left: 34%; top: 30%; width: 16%; height: 18%; border-radius: 50%; background: rgba(0,0,0,0.55); }
.bar { position: absolute; border-radius: 999px; background: rgba(255,255,255,0.10); overflow: hidden; }
.bar .fill { position: absolute; inset: 0; border-radius: 999px; background: linear-gradient(90deg, var(--c1), var(--c2)); transform-origin: left center; transform: scaleX(0); }
.bar.v .fill { transform-origin: center bottom; transform: scaleY(0); }
.wall { position: absolute; border-radius: 16px; background: linear-gradient(180deg, rgba(var(--c2rgb),0.30), rgba(var(--c2rgb),0.08)); border: 2px solid rgba(var(--c2rgb),0.55); box-shadow: inset 0 -8px 0 rgba(0,0,0,0.18); opacity: 0; }
.chip { position: absolute; border-radius: 30px; overflow: hidden; opacity: 0; background: #0b1220; border: 4px solid rgba(var(--c1rgb),0.75); box-shadow: inset 0 -12px 0 rgba(0,0,0,0.35); }
.chip .zone { position: absolute; top: 0; bottom: 0; width: 50%; }
.chip .za { left: 0; background: linear-gradient(180deg, var(--c1), rgba(0,0,0,0.30)); }
.chip .zb { right: 0; background: linear-gradient(180deg, var(--c2), rgba(0,0,0,0.30)); }
.stamp { position: absolute; display: flex; align-items: center; justify-content: center; border-radius: 999px; font-size: 26px; font-weight: 900; letter-spacing: 0.08em; color: #06210f; background: var(--c3); opacity: 0; transform: scale(0); }
.ring { position: absolute; border: 3px solid var(--c1); border-radius: 50%; opacity: 0; transform: scale(0.5); }
.lower { position: absolute; left: 54px; top: 1408px; width: 972px; height: 250px; display: flex; align-items: center; justify-content: center; z-index: 9; }
.lower .txt { font-size: 40px; font-weight: 800; line-height: 1.18; text-align: center; color: var(--ink); opacity: 0; letter-spacing: 0.005em; text-shadow: 0 4px 24px rgba(0,0,0,0.75); }
.lower .txt .line { display: block; }
/* Focal icon: large, upper-middle, always above the recipe and below the text. */
.hero { position: absolute; left: 390px; top: 540px; width: 300px; height: 300px; z-index: 7; transform-origin: 50% 50%; opacity: 0; }
.hero .halo { position: absolute; inset: -44px; border-radius: 50%; background: radial-gradient(circle, rgba(var(--c2rgb),0.30) 0%, rgba(var(--c1rgb),0.12) 46%, transparent 72%); }
.hero .disc { position: absolute; inset: 4px; border-radius: 50%; background: linear-gradient(160deg, rgba(10,15,28,0.84), rgba(6,8,13,0.66)); border: 3px solid rgba(var(--c2rgb),0.55); box-shadow: 0 0 70px rgba(var(--c2rgb),0.28), inset 0 0 44px rgba(var(--c1rgb),0.14); }
.hero svg { position: absolute; inset: 22px; width: calc(100% - 44px); height: calc(100% - 44px); color: var(--c2); filter: drop-shadow(0 0 16px rgba(var(--c2rgb),0.6)); transform-origin: 50% 50%; overflow: visible; }
.hero.t1 svg { color: var(--c1); filter: drop-shadow(0 0 16px rgba(var(--c1rgb),0.6)); }
.hero.t3 svg { color: var(--c3); filter: drop-shadow(0 0 16px rgba(var(--c3rgb),0.6)); }
.focus-tag { position: absolute; right: 60px; top: 62px; font-size: 18px; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; color: var(--c2); opacity: 0; z-index: 10; }
.progress-track { position: absolute; left: 0; top: 0; width: 1080px; height: 8px; background: rgba(255,255,255,0.10); z-index: 30; }
.progress-fill { width: 100%; height: 100%; background: linear-gradient(90deg, var(--c1), var(--c2)); transform: scaleX(0); transform-origin: left center; }
.counter { position: absolute; right: 56px; bottom: 48px; font-size: 22px; font-weight: 800; letter-spacing: 0.12em; color: var(--ink); opacity: 0; z-index: 30; }
"""


# --------------------------------------------------------------------------- #
# Small deterministic helpers
# --------------------------------------------------------------------------- #
def _esc(value: Any) -> str:
    """HTML-escape any storyboard/script authored text before embedding."""
    return html.escape(str(value), quote=True)


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce a possibly missing/string number to a finite float."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _rgb(color: str) -> str:
    """Return an 'r, g, b' triplet for hex / rgb / 'r,g,b' colour strings."""
    text = str(color or "").strip()
    if text.startswith("#"):
        hx = text.lstrip("#")
        if len(hx) == 3:
            hx = "".join(ch * 2 for ch in hx)
        if len(hx) >= 6:
            try:
                return "%d, %d, %d" % (
                    int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
                )
            except ValueError:
                pass
    parts = re.findall(r"\d+", text)
    if len(parts) >= 3:
        return "%d, %d, %d" % (int(parts[0]), int(parts[1]), int(parts[2]))
    return "34, 211, 238"


def _palette(storyboard: Dict[str, Any], topic: Dict[str, Any]) -> Dict[str, str]:
    """Normalise storyboard palette into semantic CSS colours + rgb triplets."""
    pal = storyboard.get("palette") if isinstance(storyboard, dict) else None
    pal = pal if isinstance(pal, dict) else {}

    def pick(keys: Tuple[str, ...], default: str) -> str:
        for key in keys:
            val = pal.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return default

    c1 = pick(("primary", "c1", "accent", "amber", "main"), _DEFAULT["c1"])
    c2 = pick(("secondary", "c2", "cyan", "teal", "support"), _DEFAULT["c2"])
    c3 = pick(("contrast", "c3", "highlight", "success", "green"), _DEFAULT["c3"])
    bg = pick(("background", "bg", "dark"), _DEFAULT["bg"])
    ink = pick(("ink", "text", "foreground", "light"), _DEFAULT["ink"])
    return {
        "bg": bg, "ink": ink, "c1": c1, "c2": c2, "c3": c3,
        "c1rgb": _rgb(c1), "c2rgb": _rgb(c2), "c3rgb": _rgb(c3),
    }


def _beat_starts(beats: List[Dict[str, Any]], duration: float) -> List[float]:
    """Sanitise beat timings into monotonic, in-range start times."""
    count = len(beats)
    gap = duration / max(count, 1) * 0.55
    fallback = [duration * i / max(count, 1) for i in range(count)]
    starts: List[float] = []
    for index, beat in enumerate(beats):
        raw = -1.0
        for key in ("target_s", "start", "t", "at"):
            if key in beat:
                raw = _num(beat.get(key), -1.0)
                break
        if raw < 0 or raw >= duration or (starts and raw <= starts[-1] + gap):
            raw = fallback[index]
        starts.append(raw)
    starts[0] = 0.0
    for index in range(1, count):
        floor = starts[index - 1] + gap
        if starts[index] < floor:
            starts[index] = min(floor, max(0.0, duration - gap))
    if starts:
        starts[-1] = min(starts[-1], max(0.0, duration - gap))
    return starts


def _on_screen_text(beat: Dict[str, Any], script_beat: Dict[str, Any]) -> str:
    """Return at most eight words from the storyboard's on_screen_text."""
    raw = beat.get("on_screen_text") or beat.get("text") or ""
    raw = str(raw).strip()
    if not raw and isinstance(script_beat, dict):
        raw = str(script_beat.get("focus_word") or "").strip()
    words = raw.split()
    if len(words) > 8:
        words = words[:8]
    return _esc(" ".join(words)[:72])


def _text_lines(escaped: str) -> List[str]:
    """Split an already-escaped statement into at most two balanced lines.

    The input is HTML-escaped, so rejoining its space-separated tokens with
    ``<br>`` (done by the caller) cannot inject markup.
    """
    words = escaped.split()
    if not words:
        return []
    if len(words) <= 3:
        return [" ".join(words)]
    pivot = (len(words) + 1) // 2
    return [" ".join(words[:pivot]), " ".join(words[pivot:])]


def _focus_label(beat: Dict[str, Any], script_beat: Dict[str, Any]) -> str:
    """Return a tiny corner label from the storyboard."""
    raw = beat.get("focus_label") or beat.get("label") or ""
    if not raw and isinstance(script_beat, dict):
        raw = script_beat.get("label") or beat.get("id") or ""
    return _esc(str(raw).strip()[:28])


def _template_id(beat: Dict[str, Any], index: int) -> str:
    """Resolve a storyboard template id, falling back to the 7-recipe cycle."""
    raw = str(beat.get("template_id") or beat.get("template") or "").strip().lower()
    if raw in _RECIPES:
        return raw
    if raw in _ALIASES:
        return _ALIASES[raw]
    return _RECIPES[index % len(_RECIPES)]


def _camera(beat: Dict[str, Any]) -> str:
    """Normalise a storyboard camera instruction."""
    raw = str(beat.get("camera") or "none").strip().lower()
    if raw in ("dolly_in", "dolly-in", "push_in", "push-in", "in", "push"):
        return "dolly_in"
    if raw in ("zoom_out", "zoom-out", "pull_back", "pullback", "out", "pull"):
        return "zoom_out"
    if raw in ("pan_right", "pan-right", "pan", "right"):
        return "pan_right"
    return "none"


def _int_param(params: Dict[str, Any], key: str, default: int, cap: int) -> int:
    """Read a bounded integer recipe parameter."""
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(1, min(cap, value))


# --------------------------------------------------------------------------- #
# Scene builder: HTML accumulation + deterministic tween emission
# --------------------------------------------------------------------------- #
class _Scene:
    """Collects HTML and absolute-time GSAP ``fromTo`` statements."""

    def __init__(self, total: float) -> None:
        self.html: List[str] = []
        self.js: List[str] = []
        self.total = float(total)
        self.nodes = 0

    def h(self, markup: str) -> None:
        self.html.append(markup)
        self.nodes += markup.count("<div")

    def add(self, selector: str, from_vars: str, to_vars: str, at: float) -> None:
        at = max(0.0, min(self.total, float(at)))
        self.js.append(
            'tl.fromTo("%s", {%s}, {%s, immediateRender:false}, %.3f);'
            % (selector, from_vars, to_vars, at)
        )

    def idle(
        self, selector: str, prop: str, a: float, b: float,
        t0: float, t1: float, cycle: float = 0.62, ease: str = "sine.inOut",
    ) -> None:
        """Emit finite alternating tweens so an object never rests >0.7s."""
        t, flip = float(t0), False
        while t < float(t1) - 0.08:
            seg = min(float(cycle), float(t1) - t)
            if seg < 0.14:
                break
            if not flip:
                self.add(
                    selector, "%s:%s" % (prop, a),
                    '%s:%s, duration:%.3f, ease:"%s"' % (prop, b, seg, ease), t,
                )
            else:
                self.add(
                    selector, "%s:%s" % (prop, b),
                    '%s:%s, duration:%.3f, ease:"%s"' % (prop, a, seg, ease), t,
                )
            flip = not flip
            t += seg


def _worker(sc: _Scene, ident: str, x: int, y: int, w: int, h: int, gear: bool) -> None:
    """Emit a single amber worker with a simple face (and optional gear)."""
    inner = ""
    if gear:
        inner += '<div class="gear"></div>'
    inner += '<div class="eye l"></div><div class="eye r"></div><div class="mouth"></div>'
    sc.h(
        '<div id="%s" class="worker" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;">%s</div>'
        % (ident, x, y, w, h, inner)
    )


def _tile(sc: _Scene, ident: str, x: int, y: int, size: int, extra: str = "") -> None:
    sc.h(
        '<div id="%s" class="tile%s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;"></div>'
        % (ident, extra, x, y, size, size)
    )


# --------------------------------------------------------------------------- #
# Seven object-animation recipes
# --------------------------------------------------------------------------- #
def _recipe_flood(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """White tiles stream in on staggered x tweens and bury a lone worker."""
    i, s, e, span = ctx["i"], ctx["s"], ctx["e"], ctx["span"]
    count = _int_param(ctx["params"], "count", 26, 28)
    _worker(sc, "f%d_target" % i, 430, 600, 190, 190, False)
    sc.add(
        "#f%d_target" % i, "scale:0.6, opacity:0, y:30",
        'scale:1, opacity:1, y:0, duration:0.5, ease:"power2.out"', s + 0.05,
    )
    sc.h('<div id="f%d_pile" class="cam"></div>' % i)
    for k in range(count):
        tx = 300 + (k * 67) % 520
        ty = 560 + (k * 53) % 420
        _tile(sc, "f%d_t%d" % (i, k), tx, ty, 76)
        sc.add(
            "#f%d_t%d" % (i, k), "x:-260, y:-40, opacity:0",
            'x:0, y:0, opacity:1, duration:0.55, ease:"power2.out"',
            s + 0.18 + k * 0.045,
        )
    sc.idle("#f%d_pile" % i, "y", 0, 12, s + 1.6, e, 0.6)
    sc.idle("#f%d_target" % i, "scale", 1, 1.06, s + 1.5, e, 0.7)


def _recipe_queue(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """One worker stamps tiles one at a time while a waiting line piles up."""
    i, s, e, span = ctx["i"], ctx["s"], ctx["e"], ctx["span"]
    ticks = _int_param(ctx["params"], "ticks", 5, 6)
    _worker(sc, "q%d_w" % i, 420, 560, 210, 210, True)
    sc.add(
        "#q%d_w" % i, "scale:0.5, opacity:0",
        'scale:1, opacity:1, duration:0.45, ease:"power2.out"', s + 0.05,
    )
    sc.add(
        "#q%d_w .gear" % i, "rotation:0",
        'rotation:720, duration:%.3f, ease:"none"' % span, s,
    )
    sc.h('<div id="q%d_line" class="cam"></div>' % i)
    waiting = 9
    for k in range(waiting):
        _tile(sc, "q%d_t%d" % (i, k), 60 + k * 38, 640 + (k % 2) * 20, 56)
        sc.add(
            "#q%d_t%d" % (i, k), "x:-120, opacity:0",
            'x:0, opacity:1, duration:0.4, ease:"power2.out"', s + 0.1 + k * 0.08,
        )
    sc.h("</div>")  # /line
    sc.h('<div id="q%d_out" class="cam"></div>' % i)
    step = max(0.45, (span - 1.2) / max(ticks, 1))
    for t in range(ticks):
        at = s + 0.7 + t * step
        sc.add("#q%d_w" % i, "scale:1", 'scale:1.12, duration:0.16, ease:"power2.out"', at)
        sc.add("#q%d_w" % i, "scale:1.12", 'scale:1, duration:0.20, ease:"power2.in"', at + 0.16)
        sc.add(
            "#q%d_t%d" % (i, t), "x:0, opacity:1",
            'x:360, opacity:0, duration:0.28, ease:"power2.in"', at,
        )
        _tile(sc, "q%d_o%d" % (i, t), 760, 600 + t * 54, 64, " tinted")
        sc.add(
            "#q%d_o%d" % (i, t), "scale:0, opacity:0",
            'scale:1, opacity:1, duration:0.26, ease:"back.out(1.8)"', at + 0.18,
        )
    sc.h("</div>")  # /out
    sc.idle("#q%d_line" % i, "y", 0, 7, s + 1.4, e, 0.6)
    sc.idle("#q%d_out" % i, "y", 0, 6, s + 1.4, e, 0.65)
    sc.idle("#q%d_w" % i, "y", 0, -8, s + 1.5, e, 0.65)


def _recipe_parallel_grid(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """Tiny cyan workers pop from centre, then grab tiles in a synced wave."""
    i, s, e = ctx["i"], ctx["s"], ctx["e"]
    cols = _int_param(ctx["params"], "cols", 8, 8)
    rows = _int_param(ctx["params"], "rows", 7, 7)
    sc.h('<div id="pg%d_grid" class="cam"></div>' % i)
    cw, gap = 58, 12
    step = cw + gap
    gx = (1080 - (cols * step - gap)) // 2
    gy = 380
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c
            sc.h(
                '<div id="pg%d_%d" class="mini" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;"></div>'
                % (i, k, gx + c * step, gy + r * step, cw, cw)
            )
            dist = abs(c - (cols - 1) / 2.0) + abs(r - (rows - 1) / 2.0)
            sc.add(
                "#pg%d_%d" % (i, k), "scale:0, opacity:0",
                'scale:1, opacity:1, duration:0.42, ease:"back.out(1.6)"',
                s + 0.08 + dist * 0.045,
            )
            wave = s + 0.9 + (c + r) * 0.045
            sc.add(
                "#pg%d_%d" % (i, k), 'backgroundColor:"%s"' % ctx["c2"],
                'backgroundColor:"#ffffff", duration:0.30, ease:"power2.out"', wave,
            )
            sc.add(
                "#pg%d_%d" % (i, k), "scale:1",
                'scale:1.14, duration:0.18, ease:"power2.out", repeat:1, yoyo:true',
                wave,
            )
    sc.idle("#pg%d_grid" % i, "y", 0, 10, s + 2.0, e, 0.6)
    sc.idle("#pg%d_grid" % i, "x", 0, 6, s + 2.0, e, 0.7)


def _recipe_race(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """Split screen: a slow single lane versus a fast-filling worker grid."""
    i, s, e, span = ctx["i"], ctx["s"], ctx["e"], ctx["span"]
    sc.h(
        '<div id="rc%d_ltrack" class="bar v" style="left:150px;top:480px;width:70px;height:560px;"><div class="fill"></div></div>'
        % i
    )
    sc.h(
        '<div id="rc%d_rtrack" class="bar" style="left:620px;top:900px;width:400px;height:60px;"><div class="fill"></div></div>'
        % i
    )
    sc.add(
        "#rc%d_ltrack .fill" % i, "scaleY:0",
        'scaleY:1, duration:%.3f, ease:"power2.inOut"' % (span * 0.62), s + 0.2,
    )
    sc.add(
        "#rc%d_rtrack .fill" % i, "scaleX:0",
        'scaleX:1, duration:%.3f, ease:"power2.inOut"' % (span * 0.34), s + 0.2,
    )
    sc.h('<div id="rc%d_lg" class="cam"></div>' % i)
    for k in range(6):
        _tile(sc, "rc%d_l%d" % (i, k), 90, 1000 - k * 80, 54)
        sc.add(
            "#rc%d_l%d" % (i, k), "y:60, opacity:0",
            'y:0, opacity:1, duration:0.45, ease:"power2.out"',
            s + 0.3 + k * (span * 0.6 / 6),
        )
    sc.h("</div>")  # /lg
    sc.h('<div id="rc%d_rg" class="cam"></div>' % i)
    for k in range(15):
        c, r = k % 5, k // 5
        sc.h(
            '<div id="rc%d_r%d" class="mini" style="left:%dpx;top:%dpx;width:62px;height:62px;"></div>'
            % (i, k, 620 + c * 78, 480 + r * 78)
        )
        sc.add(
            "#rc%d_r%d" % (i, k), "scale:0, opacity:0",
            'scale:1, opacity:1, duration:0.35, ease:"back.out(1.7)"',
            s + 0.25 + k * 0.05,
        )
    sc.h('<div id="rc%d_fin" class="stamp" style="left:640px;top:360px;width:240px;height:82px;">FASTER</div>' % i)
    sc.add(
        "#rc%d_fin" % i, "scale:0, opacity:0, rotation:-20",
        'scale:1, opacity:1, rotation:0, duration:0.35, ease:"back.out(2)"',
        s + span * 0.42,
    )
    sc.idle("#rc%d_rg" % i, "y", 0, 8, s + 2.0, e, 0.6)
    sc.idle("#rc%d_lg" % i, "y", 0, 6, s + 1.8, e, 0.65)
    sc.idle("#rc%d_fin" % i, "scale", 1, 1.06, s + span * 0.42 + 0.4, e, 0.7)
    sc.idle("#rc%d_ltrack .fill" % i, "opacity", 0.85, 1, s + 2.0, e, 0.7)


def _recipe_bottleneck(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """A wide flow jams through a narrow gap, then the gap widens and releases."""
    i, s, e, span = ctx["i"], ctx["s"], ctx["e"], ctx["span"]
    count = _int_param(ctx["params"], "tiles", 16, 18)
    sc.h('<div id="bn%d_wl" class="wall" style="left:180px;top:340px;width:300px;height:760px;"></div>' % i)
    sc.h('<div id="bn%d_wr" class="wall" style="left:600px;top:340px;width:300px;height:760px;"></div>' % i)
    sc.add("#bn%d_wl" % i, "x:0, opacity:0", 'x:0, opacity:1, duration:0.3', s)
    sc.add("#bn%d_wr" % i, "x:0, opacity:0", 'x:0, opacity:1, duration:0.3', s)
    sc.add("#bn%d_wl" % i, "x:0", 'x:40, duration:0.5, ease:"power2.inOut"', s + 0.1)
    sc.add("#bn%d_wr" % i, "x:0", 'x:-40, duration:0.5, ease:"power2.inOut"', s + 0.1)
    release = s + span * 0.62
    sc.add("#bn%d_wl" % i, "x:40", 'x:-30, duration:0.5, ease:"power2.inOut"', release)
    sc.add("#bn%d_wr" % i, "x:-40", 'x:30, duration:0.5, ease:"power2.inOut"', release)
    sc.h('<div id="bn%d_flow" class="cam"></div>' % i)
    for k in range(count):
        x = 120 + k * (760 // max(count - 1, 1))
        _tile(sc, "bn%d_t%d" % (i, k), x, 280, 62)
        enter = s + 0.12 + k * (max(0.2, span - 1.6) / max(count, 1))
        sc.add(
            "#bn%d_t%d" % (i, k), "y:-60, opacity:0",
            'y:420, opacity:1, duration:0.5, ease:"power2.in"',
            enter,
        )
        sc.add(
            "#bn%d_t%d" % (i, k), "y:420, opacity:1",
            'y:960, opacity:0, duration:0.5, ease:"power2.out"',
            enter + 0.62,
        )
    sc.idle("#bn%d_flow" % i, "x", 0, 5, s + 1.6, e, 0.65)
    sc.idle("#bn%d_wl" % i, "y", 0, 5, release + 0.6, e, 0.65)
    sc.idle("#bn%d_wr" % i, "y", 0, -5, release + 0.6, e, 0.65)


def _recipe_merge(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """Two coloured groups slide together and morph into one two-zone chip."""
    i, s, e = ctx["i"], ctx["s"], ctx["e"]
    per = _int_param(ctx["params"], "per_group", 8, 8)
    sc.h('<div id="mg%d_L" class="cam"></div>' % i)
    sc.h('<div id="mg%d_R" class="cam"></div>' % i)
    for k in range(per):
        col, row = k % 4, k // 4
        _tile(sc, "mg%d_L%d" % (i, k), 120 + col * 72, 480 + row * 72, 60, " tinted")
        _tile(sc, "mg%d_R%d" % (i, k), 700 + col * 72, 480 + row * 72, 60, " cyan")
    sc.add("#mg%d_L" % i, "x:-140, opacity:0", 'x:0, opacity:1, duration:0.5, ease:"power2.out"', s + 0.05)
    sc.add("#mg%d_R" % i, "x:140, opacity:0", 'x:0, opacity:1, duration:0.5, ease:"power2.out"', s + 0.05)
    sc.h(
        '<div id="mg%d_chip" class="chip" style="left:390px;top:560px;width:300px;height:300px;">'
        '<div class="zone za"></div><div class="zone zb"></div></div>' % i
    )
    sc.add(
        "#mg%d_chip" % i, "scale:0.2, opacity:0, rotation:-18",
        'scale:1, opacity:1, rotation:0, duration:0.6, ease:"back.out(1.5)"', s + 0.7,
    )
    sc.add("#mg%d_L" % i, "opacity:1, scale:1", 'opacity:0, scale:0.85, duration:0.35, ease:"power2.in"', s + 0.75)
    sc.add("#mg%d_R" % i, "opacity:1, scale:1", 'opacity:0, scale:0.85, duration:0.35, ease:"power2.in"', s + 0.75)
    sc.idle("#mg%d_chip" % i, "scale", 1, 1.05, s + 1.5, e, 0.65)
    sc.idle("#mg%d_chip" % i, "opacity", 0.9, 1, s + 1.5, e, 0.7)


def _recipe_payoff(sc: _Scene, ctx: Dict[str, Any]) -> None:
    """A mosaic pulls back into a check-mark picture, then gently glows."""
    i, s, e = ctx["i"], ctx["s"], ctx["e"]
    grid = _int_param(ctx["params"], "grid", 7, 7)
    keep = {(2, 6), (2, 5), (3, 5), (3, 4), (3, 1),
            (4, 4), (4, 3), (4, 2), (5, 3), (5, 2)}
    sc.h('<div id="po%d_mosaic" class="cam"></div>' % i)
    size, gap = 84, 12
    step = size + gap
    gx = (1080 - (grid * step - gap)) // 2
    gy = 360
    for r in range(grid):
        for c in range(grid):
            k = r * grid + c
            x = gx + c * step
            y = gy + r * step
            _tile(sc, "po%d_%d" % (i, k), x, y, size)
            sc.add(
                "#po%d_%d" % (i, k), "scale:0.4, opacity:0",
                'scale:1, opacity:1, duration:0.4, ease:"back.out(1.5)"',
                s + 0.08 + (r + c) * 0.03,
            )
            if (r, c) not in keep:
                sc.add(
                    "#po%d_%d" % (i, k), "scale:1, opacity:1",
                    'scale:0, opacity:0, duration:0.35, ease:"power2.in"',
                    s + 1.0 + (r + c) * 0.02,
                )
            else:
                sc.add(
                    "#po%d_%d" % (i, k), "opacity:1",
                    'opacity:0.72, duration:0.5, ease:"sine.inOut", repeat:1, yoyo:true',
                    s + 1.4 + (r + c) * 0.02,
                )
    sc.add(
        "#po%d_mosaic" % i, "scale:1.12",
        'scale:0.92, duration:%.3f, ease:"power2.inOut"' % (span_safe(ctx)), s + 0.4,
    )
    sc.idle("#po%d_mosaic" % i, "y", 0, 10, s + 1.8, e, 0.7)


def span_safe(ctx: Dict[str, Any]) -> float:
    """Return a clamped tween span for the payoff pull-back."""
    return max(0.4, min(ctx["span"] * 0.6, ctx["e"] - ctx["s"] - 0.6))


_RECIPE_FNS = {
    "flood": _recipe_flood,
    "queue": _recipe_queue,
    "parallel_grid": _recipe_parallel_grid,
    "race": _recipe_race,
    "bottleneck": _recipe_bottleneck,
    "merge": _recipe_merge,
    "payoff": _recipe_payoff,
}


# --------------------------------------------------------------------------- #
# Public builder
# --------------------------------------------------------------------------- #
def build_short_html_v3(
    topic: dict, script: dict, storyboard: dict, words: list, duration: float
) -> str:
    """Return a complete, self-contained object-animation HyperFrames document.

    Args:
        topic: topic dict (title/pillar are used only for the page title).
        script: output of ``short_script`` (beats + narration); supplies beat
            ordering, labels and fallback on-screen text.
        storyboard: dict with a ``palette`` mapping and a ``beats`` list. Each
            storyboard beat may define ``template_id``, ``icon``,
            ``on_screen_text``, ``focus_label``, ``params``, ``camera`` and
            ``visual_metaphor``. ``icon`` literally depicts the beat's noun
            (chef/cupcake/cpu/grid/clock/bolt/check/queue/funnel/none).
        words: ``[{"text", "start", "end"}]``; used sparingly to pulse a small
            accent ring on each beat's first spoken word.
        duration: final narration duration in seconds.
    """
    topic = topic if isinstance(topic, dict) else {}
    script = script if isinstance(script, dict) else {}
    storyboard = storyboard if isinstance(storyboard, dict) else {}
    words = words if isinstance(words, list) else []

    total = max(0.5, _num(duration, 1.0))
    dstr = "%.1f" % total
    colors = _palette(storyboard, topic)
    title = _esc(script.get("title") or topic.get("title") or "Short")

    script_beats: List[Dict[str, Any]] = [
        beat if isinstance(beat, dict) else {}
        for beat in (script.get("beats") or [])
    ]
    sb_beats_raw = storyboard.get("beats")
    sb_beats: List[Dict[str, Any]] = [
        beat if isinstance(beat, dict) else {}
        for beat in (sb_beats_raw if isinstance(sb_beats_raw, list) else [])
    ]
    if not sb_beats:
        sb_beats = list(script_beats)
    if not sb_beats:
        sb_beats = [{} for _ in range(7)]

    count = len(sb_beats)
    starts = _beat_starts(sb_beats, total)
    ends = [starts[i + 1] if i + 1 < count else total for i in range(count)]

    sc = _Scene(total)

    # --- DOM ----------------------------------------------------------------
    sc.h(
        '<div id="root" data-composition-id="main" data-start="0" '
        'data-duration="%s" data-width="1080" data-height="1920">' % dstr
    )
    sc.h(
        '<audio id="narration" src="narration_master.wav" data-start="0" '
        'data-duration="%s" data-volume="1"></audio>' % dstr
    )
    sc.h('<div id="bg-canvas" class="bg-canvas"></div>')
    sc.h('<div id="grid-bg" class="grid-bg"></div>')
    sc.h('<div id="orb1" class="orb a" style="left:-120px;top:180px;"></div>')
    sc.h('<div id="orb2" class="orb b" style="left:640px;top:1080px;"></div>')
    sc.h('<div id="orb3" class="orb c" style="left:280px;top:560px;"></div>')
    sc.h('<div id="sweep" class="sweep"></div>')
    sc.h('<div id="world" class="world">')

    first_word_at: List[float] = []
    for index, beat in enumerate(sb_beats):
        s, e = starts[index], ends[index]
        span = max(0.6, e - s)
        script_beat = script_beats[index] if index < len(script_beats) else {}
        params = beat.get("params") if isinstance(beat.get("params"), dict) else {}

        sc.h(
            '<div id="beat%d" class="beat" data-start="%.1f" data-duration="%.1f" data-track-index="0">'
            % (index, s, max(0.0, e - s))
        )
        sc.h('<div id="cam%d" class="cam">' % index)

        template = _template_id(beat, index)
        ctx = {
            "i": index, "s": s, "e": e, "span": span,
            "c1": colors["c1"], "c2": colors["c2"], "c3": colors["c3"],
            "params": params, "beat": beat,
        }
        _RECIPE_FNS[template](sc, ctx)

        sc.h("</div>")  # /cam

        # Focal icon: the literal noun of the beat, large in the upper-middle.
        # It sits above the moving recipe (z-index 7) and below the statement.
        icon = _icon(beat, index, template)
        sc.h(
            '<div id="hero%d" class="hero t%d" data-icon="%s">'
            '<div class="halo"></div><div class="disc"></div>%s</div>'
            % (index, _ICON_TONE[icon], icon, _hero_svg(icon))
        )

        text = _on_screen_text(beat, script_beat)
        if text:
            lines = _text_lines(text)
            body = "<br>".join(
                '<span class="line">%s</span>' % line for line in lines
            )
            sc.h(
                '<div class="lower"><div class="txt" id="lot%d">%s</div></div>'
                % (index, body)
            )
        focus = _focus_label(beat, script_beat)
        if focus:
            sc.h('<div class="focus-tag" id="ft%d">%s</div>' % (index, focus))
        sc.h(
            '<div class="ring" id="ac%d" style="left:940px;top:1330px;width:54px;height:54px;"></div>'
            % index
        )
        sc.h("</div>")  # /beat

        # First spoken word inside this beat drives a subtle accent pulse.
        found = None
        for item in words:
            if not isinstance(item, dict):
                continue
            ws = _num(item.get("start"), -1.0)
            if s <= ws < e:
                found = ws
                break
        first_word_at.append(found)

    sc.h("</div>")  # /world
    sc.h('<div class="progress-track"><div class="progress-fill" id="progress"></div></div>')
    for index in range(count):
        sc.h(
            '<div class="counter" id="cnt%d">%02d / %02d</div>'
            % (index, index + 1, count)
        )
    sc.h("</div>")  # /root

    # --- Deterministic paused timeline --------------------------------------
    js: List[str] = [
        "window.__timelines = window.__timelines || {};",
        'window.__timelines["main"] = gsap.timeline({paused:true});',
        'const tl = window.__timelines["main"];',
    ]

    # Global ambient motion.
    sc.add("#progress", "scaleX:0", 'scaleX:1, duration:%.3f, ease:"none"' % total, 0)
    # Bounded loops keep the picture moving for the entire video. A one-way
    # drift eventually leaves the frame, which made later beats look static.
    sc.add("#world", "scale:1", 'scale:1.10, duration:%.3f, ease:"none"' % total, 0)
    sc.idle("#grid-bg", "x", 0, 64, 0, total, 0.9, "none")
    sc.idle("#grid-bg", "y", 0, 64, 0, total, 1.3, "none")
    sc.add("#bg-canvas", "opacity:0.85", 'opacity:1, duration:%.3f, ease:"none"' % total, 0)
    sc.idle("#orb1", "x", -180, 180, 0, total, 2.3, "sine.inOut")
    sc.idle("#orb1", "y", -90, 90, 0, total, 3.1, "sine.inOut")
    sc.idle("#orb2", "x", 160, -160, 0, total, 2.7, "sine.inOut")
    sc.idle("#orb2", "y", -80, 80, 0, total, 3.5, "sine.inOut")
    sc.idle("#orb3", "x", -140, 140, 0, total, 2.1, "sine.inOut")
    sc.idle("#orb3", "y", 100, -100, 0, total, 2.9, "sine.inOut")
    sc.idle("#sweep", "x", -320, 320, 0, total, 1.4, "none")

    for index, beat in enumerate(sb_beats):
        s, e = starts[index], ends[index]
        span = max(0.6, e - s)
        in_dur = min(0.45, span * 0.28)
        exit_at = max(s + in_dur + 0.35, e - 0.22)
        out_dur = 0.22

        # Camera per storyboard beat.
        cam = _camera(beat)
        if cam == "dolly_in":
            sc.add("#cam%d" % index, "scale:1", 'scale:1.05, duration:%.3f, ease:"power2.inOut"' % span, s)
        elif cam == "zoom_out":
            sc.add("#cam%d" % index, "scale:1.05", 'scale:1, duration:%.3f, ease:"power2.inOut"' % span, s)
        elif cam == "pan_right":
            sc.add("#cam%d" % index, "x:60", 'x:-60, duration:%.3f, ease:"power2.inOut"' % span, s)
        else:
            sc.add("#cam%d" % index, "x:0, y:0", 'x:14, y:-10, duration:%.3f, ease:"power2.inOut"' % span, s)

        # Entry: clip-path wipe + quick zoom punch.
        sc.add(
            "#beat%d" % index, 'clipPath:"inset(0 100% 0 0)"',
            'clipPath:"inset(0 0%% 0 0)", duration:%.3f, ease:"power2.inOut"' % in_dur, s,
        )
        sc.add(
            "#beat%d" % index, "scale:1.03",
            'scale:1, duration:%.3f, ease:"power2.inOut"' % in_dur, s,
        )
        # Exit: faster wipe out.
        sc.add(
            "#beat%d" % index, 'clipPath:"inset(0 0% 0 0)"',
            'clipPath:"inset(0 0 0 100%%)", duration:%.3f, ease:"power2.in"' % out_dur, exit_at,
        )
        sc.add(
            "#beat%d" % index, "scale:1",
            'scale:1.05, duration:%.3f, ease:"power2.in"' % out_dur, exit_at,
        )

        # Focal icon: present for the whole beat, with small bounded idle
        # motion (breathing + gentle tilt). All tweens are absolute-time
        # fromTo statements on the paused timeline, so frame seeking works.
        template = _template_id(beat, index)
        icon = _icon(beat, index, template)
        hero = "#hero%d" % index
        sc.add(
            hero, "scale:0.62, opacity:0, y:36",
            'scale:1, opacity:1, y:0, duration:0.42, ease:"back.out(1.7)"',
            s + 0.05,
        )
        idle_from = min(e - 0.05, s + 0.52)
        if idle_from > s + 0.1:
            sc.idle(hero, "scale", 1, 1.06, idle_from, e, 0.72)
            sc.idle(hero, "y", 0, -9, idle_from, e, 0.66)
            sc.idle(hero + " svg", "rotation", -3.5, 3.5, idle_from, e, 0.86)
        out_at = max(s + span * 0.5, exit_at - 0.06)
        sc.add(hero, "opacity:1", 'opacity:0, duration:0.22, ease:"power2.in"', out_at)

        # Lower-third and corner-label fades carry no meaning themselves.
        if _on_screen_text(beat, script_beats[index] if index < len(script_beats) else {}):
            sc.add(
                "#lot%d" % index, "y:26, opacity:0",
                'y:0, opacity:1, duration:0.4, ease:"power2.out"', s + 0.12,
            )
            sc.add(
                "#lot%d" % index, "y:0, opacity:1",
                'y:-18, opacity:0, duration:%.3f, ease:"power2.in"' % out_dur, exit_at,
            )
        if _focus_label(beat, script_beats[index] if index < len(script_beats) else {}):
            sc.add(
                "#ft%d" % index, "x:-18, opacity:0",
                'x:0, opacity:1, duration:0.4, ease:"power2.out"', s + 0.08,
            )
            sc.add(
                "#ft%d" % index, "x:0, opacity:1",
                'x:18, opacity:0, duration:%.3f, ease:"power2.in"' % out_dur, exit_at,
            )

        # UI beat counter.
        sc.add("#cnt%d" % index, "opacity:0", "opacity:1, duration:0.2", s)
        sc.add("#cnt%d" % index, "opacity:1", "opacity:0, duration:0.2", exit_at)

        # Sparingly-used word timing: one accent pulse per beat.
        pulse_at = first_word_at[index]
        if pulse_at is None:
            pulse_at = s + 0.2
        sc.add(
            "#ac%d" % index, "scale:0.5, opacity:0.85",
            'scale:1.6, opacity:0, duration:0.5, ease:"power2.out"', pulse_at,
        )

    js.extend(sc.js)

    variables = (
        ":root{--bg:%s;--ink:%s;--c1:%s;--c2:%s;--c3:%s;"
        "--c1rgb:%s;--c2rgb:%s;--c3rgb:%s;}\n"
        % (
            colors["bg"], colors["ink"], colors["c1"], colors["c2"], colors["c3"],
            colors["c1rgb"], colors["c2rgb"], colors["c3rgb"],
        )
    )

    document = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8" />',
        "<title>%s • Vertical Short</title>" % title,
        '<script src="%s"></script>' % GSAP_CDN,
        "<style>",
        variables + _CSS,
        "</style>",
        "</head>",
        "<body>",
        "\n".join(sc.html),
        "<script>",
        "\n".join(js),
        "</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(document)
