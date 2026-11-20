"""Last-resort provider: guarantees every scene has a renderable visual."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from .base import VisualProvider, make_asset, scene_concept, scene_visual_type

try:
    from .illustration_provider import IllustrationProvider
except Exception:  # pragma: no cover - defensive
    IllustrationProvider = None  # type: ignore
try:
    from .diagram_provider import DiagramProvider
except Exception:  # pragma: no cover - defensive
    DiagramProvider = None  # type: ignore

_EMERGENCY_SVG = (
    '<div class="vp-illustration" data-icon="cpu">'
    '<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" fill="none" '
    'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<rect x="12" y="12" width="24" height="24" rx="4"/>'
    '<rect x="19" y="19" width="10" height="10" rx="2"/>'
    '</svg></div>'
)


class FallbackProvider(VisualProvider):
    name = "fallback"

    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        return True

    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        markup = ""
        kind = "emergency"
        kind_text = scene_visual_type(scene)
        try:
            diagram_like = any(
                word in kind_text for word in ("diagram", "chart", "flow", "graph", "pipeline")
            )
            if diagram_like and DiagramProvider is not None:
                asset = DiagramProvider().resolve(scene, topic, cache, ledger)
                if asset:
                    return make_asset(
                        self.name,
                        "markup",
                        inline_markup=asset["inline_markup"],
                        license="MIT/Own-generated",
                        attribution="Own-generated fallback diagram",
                        sha256=asset["sha256"],
                        relevance_score=0.5,
                    )
            if IllustrationProvider is not None:
                asset = IllustrationProvider().resolve(scene, topic, cache, ledger)
                if asset:
                    return make_asset(
                        self.name,
                        "markup",
                        inline_markup=asset["inline_markup"],
                        license="MIT/Own-generated",
                        attribution="Own-generated fallback illustration",
                        sha256=asset["sha256"],
                        relevance_score=0.5,
                    )
        except Exception:
            markup = ""
        if not markup:
            markup = _EMERGENCY_SVG
            kind = "emergency"
        digest = hashlib.sha256(markup.encode("utf-8")).hexdigest()
        return make_asset(
            self.name,
            "markup",
            inline_markup=markup,
            license="MIT/Own-generated",
            attribution="Own-generated fallback visual (%s): %s" % (
                kind, scene_concept(scene, topic)[:60]
            ),
            sha256=digest,
            relevance_score=0.5,
        )
