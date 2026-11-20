"""Self-contained inline-SVG diagram generator (no external assets)."""
from __future__ import annotations

import hashlib
import html
import re
from typing import Any, Dict, Optional

from .base import VisualProvider, make_asset, scene_concept, scene_visual_type

_KINDS = ("flow", "layers", "grid", "queue", "chart", "compare")

_KEYWORDS = {
    "flow": ("flow", "process", "pipeline", "steps", "workflow", "sequence", "pipeline"),
    "layers": ("layer", "stack", "tier", "architecture", "hierarchy", "levels", "model"),
    "grid": ("grid", "matrix", "parallel", "workers", "cells", "table"),
    "queue": ("queue", "serial", "line", "wait", "bottleneck", "funnel", "throughput"),
    "chart": ("chart", "graph", "bar", "data", "metrics", "growth", "numbers", "statistics"),
    "compare": ("compare", "versus", "vs", "split", "difference", "against", "two"),
}

_SUPPORTED_TYPES = {
    "diagram", "diagrams", "chart", "charts", "flow", "flowchart", "flow_diagram",
    "graph", "pipeline", "architecture", "layers", "queue", "grid", "infographic",
    "visualization", "process",
}

_W = 960
_H = 540


def _label(text: str, limit: int = 28) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) > limit:
        clean = clean[: limit - 1].rstrip() + "…"
    return html.escape(clean)


def _svg_open() -> str:
    return (
        '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
        'fill="none" stroke="currentColor" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round" role="img" '
        'aria-label="generated diagram">' % (_W, _H)
    )


def _text(x: int, y: int, value: str, size: int = 26, anchor: str = "middle") -> str:
    return (
        '<text x="%d" y="%d" text-anchor="%s" font-size="%d" fill="currentColor" '
        'stroke="none" font-family="system-ui, sans-serif">%s</text>'
        % (x, y, anchor, size, _label(value))
    )


def _arrow(x1: int, y: int, x2: int) -> str:
    return (
        '<path d="M%d %d H%d M%d %d l-12 -8 M%d %d l-12 8"/>'
        % (x1, y, x2 - 14, x2, y, x2, y)
    )


def _flow(concept: str) -> str:
    words = [w for w in re.split(r"\s+", concept) if w][:3] or ["Input", "Process", "Output"]
    out = [_svg_open(), _text(480, 70, "FLOW", 30)]
    for idx, word in enumerate(words):
        x = 70 + idx * 300
        out.append('<rect x="%d" y="200" width="220" height="120" rx="16"/>' % x)
        out.append(_text(x + 110, 245, word, 24))
        out.append(_text(x + 110, 285, "step %d" % (idx + 1), 18))
        if idx < len(words) - 1:
            out.append(_arrow(x + 220, 260, x + 300))
    out.append("</svg>")
    return "".join(out)


def _layers(concept: str) -> str:
    names = [w for w in re.split(r"\s+", concept) if w][:4] or ["Application", "Logic", "Data", "Infra"]
    out = [_svg_open(), _text(480, 70, "LAYERS", 30)]
    for idx, name in enumerate(names):
        y = 110 + idx * 100
        out.append('<rect x="230" y="%d" width="500" height="76" rx="14"/>' % y)
        out.append(_text(480, y + 48, name, 24))
    out.append("</svg>")
    return "".join(out)


def _grid(concept: str) -> str:
    out = [_svg_open(), _text(480, 70, "PARALLEL GRID", 30)]
    for row in range(3):
        for col in range(5):
            x, y = 130 + col * 145, 130 + row * 125
            fill = ' fill="currentColor" fill-opacity="0.35"' if (row + col) % 3 == 0 else ""
            out.append('<rect x="%d" y="%d" width="110" height="90" rx="12"%s/>' % (x, y, fill))
    out.append(_text(480, 510, _label(concept, 45), 20))
    out.append("</svg>")
    return "".join(out)


def _queue(concept: str) -> str:
    out = [_svg_open(), _text(480, 70, "QUEUE", 30)]
    for idx in range(5):
        x = 100 + idx * 160
        out.append('<circle cx="%d" cy="250" r="38"/>' % x)
        out.append(_text(x, 258, str(idx + 1), 24))
        if idx < 4:
            out.append(_arrow(x + 38, 250, x + 160))
    out.append('<rect x="330" y="390" width="300" height="90" rx="14"/>')
    out.append(_text(480, 445, "PROCESSING", 24))
    out.append("</svg>")
    return "".join(out)


def _chart(concept: str) -> str:
    values = [90, 160, 130, 230, 200, 300, 270]
    out = [_svg_open(), _text(480, 70, "METRICS", 30)]
    out.append('<path d="M120 460 H860 M120 460 V120"/>')
    for idx, value in enumerate(values):
        x = 170 + idx * 100
        out.append(
            '<rect x="%d" y="%d" width="56" height="%d" rx="8" '
            'fill="currentColor" fill-opacity="0.45" stroke="none"/>'
            % (x, 460 - value, value)
        )
    out.append(_text(480, 510, _label(concept, 45), 20))
    out.append("</svg>")
    return "".join(out)


def _compare(concept: str) -> str:
    out = [_svg_open(), _text(480, 70, "COMPARE", 30)]
    out.append('<rect x="90" y="140" width="340" height="300" rx="18"/>')
    out.append('<rect x="530" y="140" width="340" height="300" rx="18"/>')
    out.append(_text(260, 300, "OPTION A", 26))
    out.append(_text(700, 300, "OPTION B", 26))
    out.append(_text(480, 300, "VS", 34))
    out.append(_text(480, 500, _label(concept, 45), 20))
    out.append("</svg>")
    return "".join(out)


_RENDER = {
    "flow": _flow,
    "layers": _layers,
    "grid": _grid,
    "queue": _queue,
    "chart": _chart,
    "compare": _compare,
}


def pick_kind(scene: Dict[str, Any], topic: Any) -> str:
    """Choose a diagram kind from visual_type and concept keywords."""
    raw = scene_visual_type(scene).lower()
    for kind in _KINDS:
        if kind in raw:
            return kind
    text = scene_concept(scene, topic).lower()
    scores: Dict[str, int] = {kind: 0 for kind in _KINDS}
    for kind, words in _KEYWORDS.items():
        for word in words:
            if word and word in text:
                scores[kind] += 1
    best = max(scores, key=lambda key: scores[key])
    return best if scores[best] else "flow"


def render_diagram(kind: str, concept: str) -> str:
    return _RENDER.get(kind, _flow)(concept)


class DiagramProvider(VisualProvider):
    name = "diagram"

    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        kind = scene_visual_type(scene)
        return kind in _SUPPORTED_TYPES or any(k in kind for k in _KINDS)

    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        try:
            kind = pick_kind(scene, topic)
            concept = str(scene.get("main_visual_concept") or scene_concept(scene, topic))
            markup = (
                '<div class="vp-diagram" data-diagram="%s">%s</div>'
                % (html.escape(kind), render_diagram(kind, concept))
            )
            digest = hashlib.sha256(markup.encode("utf-8")).hexdigest()
            return make_asset(
                self.name,
                "markup",
                inline_markup=markup,
                license="MIT/Own-generated",
                attribution="Own-generated inline SVG diagram (%s)" % kind,
                sha256=digest,
                relevance_score=0.9,
            )
        except Exception:
            return None
