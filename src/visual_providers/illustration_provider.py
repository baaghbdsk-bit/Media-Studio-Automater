"""Zero-cost illustration provider built on the existing icon vocabulary.

It reuses ``_ICON_SVGS`` / ``_ICON_TONE`` / ``_ICON_BY_TEMPLATE`` from
``short_visual_v3`` when importable, so no SVG code is duplicated. A tiny
defensive fallback keeps this module importable in isolation.
"""
from __future__ import annotations

import hashlib
import html
import re
from typing import Any, Dict, Optional

from .base import VisualProvider, make_asset, scene_concept, scene_visual_type

_ICON_SVGS: Dict[str, str] = {}
_ICON_TONE: Dict[str, int] = {}
_ICON_BY_TEMPLATE: Dict[str, str] = {}

try:  # package import (src.visual_providers.*)
    from ..short_visual_v3 import (  # type: ignore
        _ICON_SVGS as _UPSTREAM_SVGS,
        _ICON_TONE as _UPSTREAM_TONE,
        _ICON_BY_TEMPLATE as _UPSTREAM_BY_TEMPLATE,
    )
    _ICON_SVGS, _ICON_TONE, _ICON_BY_TEMPLATE = (
        dict(_UPSTREAM_SVGS),
        dict(_UPSTREAM_TONE),
        dict(_UPSTREAM_BY_TEMPLATE),
    )
except Exception:  # pragma: no cover - fallback path
    try:  # flat import when src/ is on sys.path
        from short_visual_v3 import (  # type: ignore
            _ICON_SVGS as _UPSTREAM_SVGS,
            _ICON_TONE as _UPSTREAM_TONE,
            _ICON_BY_TEMPLATE as _UPSTREAM_BY_TEMPLATE,
        )
        _ICON_SVGS, _ICON_TONE, _ICON_BY_TEMPLATE = (
            dict(_UPSTREAM_SVGS),
            dict(_UPSTREAM_TONE),
            dict(_UPSTREAM_BY_TEMPLATE),
        )
    except Exception:
        pass

# Minimal self-contained fallback (only used if the import above fails).
if not _ICON_SVGS:  # pragma: no cover - defensive
    _ICON_SVGS = {
        "cpu": '<rect x="12" y="12" width="24" height="24" rx="4"/>'
               '<rect x="19" y="19" width="10" height="10" rx="2"/>',
        "check": '<circle cx="24" cy="24" r="18"/><path d="m14 25 7 7 14-16"/>',
        "bolt": '<path d="M27 3 11 27h11l-2 18 18-24H26z"/>',
        "grid": "".join(
            '<rect x="%d" y="%d" width="10" height="10" rx="2"/>'
            % (7 + c * 12, 7 + r * 12)
            for r in range(3) for c in range(3)
        ),
    }
    _ICON_TONE = {"check": 3, "bolt": 1, "cpu": 2, "grid": 2}
    _ICON_BY_TEMPLATE = {"payoff": "check", "race": "bolt", "merge": "cpu", "grid": "grid"}

_KEYWORD_ICON = {
    "check": "check", "success": "check", "result": "check", "final": "check",
    "done": "check", "speed": "bolt", "fast": "bolt", "power": "bolt",
    "time": "clock", "clock": "clock", "wait": "clock", "slow": "clock",
    "queue": "queue", "line": "queue", "serial": "queue", "people": "queue",
    "funnel": "funnel", "filter": "funnel", "narrow": "funnel", "limit": "funnel",
    "grid": "grid", "parallel": "grid", "workers": "grid", "matrix": "grid",
    "cpu": "cpu", "ai": "cpu", "chip": "cpu", "compute": "cpu", "model": "cpu",
    "bake": "chef", "chef": "chef", "cook": "chef", "recipe": "chef",
    "cake": "cupcake", "cupcake": "cupcake", "dessert": "cupcake", "sweet": "cupcake",
}

_SUPPORTED_TYPES = {
    "illustration", "illustrative", "icon", "concept", "hero", "analogy",
    "metaphor", "subject", "art", "symbol",
}


def _icon_svg(name: str) -> str:
    body = _ICON_SVGS.get(name) or _ICON_SVGS.get("cpu") or ""
    return (
        '<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" '
        'fill="none" stroke="currentColor" stroke-width="2.4" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        "%s</svg>" % body
    )


def _pick_icon(scene: Dict[str, Any], topic: Any) -> str:
    raw = str(scene.get("icon") or scene.get("visual_type") or "").strip().lower()
    if raw in _ICON_SVGS:
        return raw
    text = scene_concept(scene, topic).lower()
    template = re.sub(r"[^a-z_]", "", raw)
    if template in _ICON_BY_TEMPLATE:
        return _ICON_BY_TEMPLATE[template]
    for keyword, icon in _KEYWORD_ICON.items():
        if keyword in text and icon in _ICON_SVGS:
            return icon
    return "cpu" if "cpu" in _ICON_SVGS else next(iter(_ICON_SVGS), "icon")


class IllustrationProvider(VisualProvider):
    name = "illustration"

    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        return scene_visual_type(scene) in _SUPPORTED_TYPES

    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        try:
            icon = _pick_icon(scene, topic)
            tone = int(_ICON_TONE.get(icon, 2))
            markup = (
                '<div class="vp-illustration" data-icon="%s" data-tone="%s">%s</div>'
                % (html.escape(icon), tone, _icon_svg(icon))
            )
            digest = hashlib.sha256(markup.encode("utf-8")).hexdigest()
            return make_asset(
                self.name,
                "markup",
                inline_markup=markup,
                license="MIT/Own-generated",
                attribution="Own-generated inline SVG (short_visual_v3 icon vocabulary)",
                sha256=digest,
                relevance_score=0.9,
            )
        except Exception:
            return None
