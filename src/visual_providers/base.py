"""Shared contracts for license-aware visual asset providers.

Every provider returns the *exact* asset dictionary shape consumed by the
orchestrator manifest::

    {
      "provider": str, "type": "image|video|markup",
      "local_path": str, "inline_markup": str, "source_url": str,
      "license": str, "attribution": str, "sha256": str,
      "relevance_score": float,
    }

No provider performs network access at import time, and no provider crashes
the pipeline on failure -- ``resolve`` returns ``None`` and the orchestrator
moves to the next provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Keep this tuple in sync with the manifest contract (exact key set).
ASSET_KEYS = (
    "provider",
    "type",
    "local_path",
    "inline_markup",
    "source_url",
    "license",
    "attribution",
    "sha256",
    "relevance_score",
)


class ResolvedAsset(dict):
    """A dict with the canonical asset keys and safe defaults."""

    def __init__(
        self,
        provider: str = "",
        asset_type: str = "image",
        *,
        local_path: str = "",
        inline_markup: str = "",
        source_url: str = "",
        license: str = "",
        attribution: str = "",
        sha256: str = "",
        relevance_score: float = 0.0,
    ) -> None:
        super().__init__(
            {
                "provider": str(provider),
                "type": str(asset_type),
                "local_path": str(local_path),
                "inline_markup": str(inline_markup),
                "source_url": str(source_url),
                "license": str(license),
                "attribution": str(attribution),
                "sha256": str(sha256),
                "relevance_score": float(relevance_score),
            }
        )


def make_asset(provider: str = "", asset_type: str = "image", **kwargs: Any) -> ResolvedAsset:
    """Helper that builds a canonical asset dict from keyword arguments."""
    return ResolvedAsset(provider, asset_type, **kwargs)


def is_valid_asset(asset: Any) -> bool:
    """True when *asset* has the exact manifest key set and a valid type."""
    return (
        isinstance(asset, dict)
        and all(key in asset for key in ASSET_KEYS)
        and asset.get("type") in ("image", "video", "markup")
    )


def scene_visual_type(scene: Dict[str, Any]) -> str:
    """Lower-cased visual_type of a scene (empty string when absent)."""
    return str((scene or {}).get("visual_type") or "").strip().lower()


def scene_concept(scene: Dict[str, Any], topic: Any = None) -> str:
    """Human-readable concept text used for queries and keyword routing."""
    scene = scene or {}
    parts = [
        str(scene.get("main_visual_concept") or ""),
        str(scene.get("visual_type") or ""),
        str(scene.get("icon") or ""),
    ]
    span = scene.get("narration_span")
    if isinstance(span, dict):
        parts.append(str(span.get("text") or span.get("narration") or ""))
    if isinstance(topic, dict):
        parts.append(str(topic.get("title") or topic.get("topic") or ""))
    elif topic:
        parts.append(str(topic))
    return " ".join(p for p in parts if p).strip()


class VisualProvider(ABC):
    """Abstract base for all visual asset providers."""

    name = "visual-provider"

    @abstractmethod
    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        """Whether this provider should be tried for the given scene."""

    @abstractmethod
    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        """Return a canonical asset dict, or ``None`` if it cannot resolve one."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "<%s name=%r>" % (self.__class__.__name__, self.name)
