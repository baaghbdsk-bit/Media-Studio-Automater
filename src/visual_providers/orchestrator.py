"""License-aware visual plan resolver.

Public entry point::

    resolve_plan(plan: dict, topic: dict, cache_root: str | None = None) -> dict

Providers are tried in a fixed priority order; each one is isolated in a
try/except so a single failure can never crash the pipeline. The returned
manifest matches the agreed scene/asset contract exactly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:  # package import
    from ..asset_cache import AssetCache
    from ..license_ledger import LicenseLedger
except Exception:  # pragma: no cover - flat import fallback
    from asset_cache import AssetCache  # type: ignore
    from license_ledger import LicenseLedger  # type: ignore
from .base import is_valid_asset, make_asset
from .diagram_provider import DiagramProvider
from .fallback_provider import FallbackProvider
from .illustration_provider import IllustrationProvider
from .official_media_provider import OfficialMediaProvider
from .stock_provider import StockProvider
from .ui_mock_provider import UiMockProvider

_RELEVANCE_DEFAULTS = {
    "official_media": 0.95,
    "stock": 0.7,
    "diagram": 0.9,
    "chart": 0.9,
    "ui_mock": 0.9,
    "illustration": 0.9,
    "fallback": 0.5,
}

_EMERGENCY_SVG = (
    '<div class="vp-illustration" data-icon="cpu">'
    '<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" fill="none" '
    'stroke="currentColor" stroke-width="2.4"><rect x="12" y="12" '
    'width="24" height="24" rx="4"/><rect x="19" y="19" width="10" '
    'height="10" rx="2"/></svg></div>'
)


def _providers() -> List[Any]:
    """Priority order: official -> stock -> diagram -> UI -> illustration -> fallback."""
    return [
        OfficialMediaProvider(),
        StockProvider(),
        DiagramProvider(),
        UiMockProvider(),
        IllustrationProvider(),
        FallbackProvider(),
    ]


def _emergency_asset() -> dict:
    import hashlib

    digest = hashlib.sha256(_EMERGENCY_SVG.encode("utf-8")).hexdigest()
    return make_asset(
        "fallback",
        "markup",
        inline_markup=_EMERGENCY_SVG,
        license="MIT/Own-generated",
        attribution="Own-generated emergency inline SVG",
        sha256=digest,
        relevance_score=0.5,
    )


def _normalize_asset(asset: Optional[dict]) -> dict:
    """Guarantee a canonical, license-clean asset dict."""
    if not is_valid_asset(asset):
        return _emergency_asset()
    asset = dict(asset)
    provider = str(asset.get("provider") or "")
    score = asset.get("relevance_score")
    if not isinstance(score, (int, float)) or float(score) <= 0:
        asset["relevance_score"] = _RELEVANCE_DEFAULTS.get(provider, 0.7)
    else:
        asset["relevance_score"] = float(score)
    return asset


def _resolve_scene(
    scene: Dict[str, Any], topic: Any, cache: AssetCache, ledger: LicenseLedger, providers: List[Any]
) -> dict:
    for provider in providers:
        try:
            if not provider.supports(scene, topic):
                continue
            candidate = provider.resolve(scene, topic, cache, ledger)
            if candidate is None:
                continue
            if not is_valid_asset(candidate) or not ledger.accept(candidate):
                continue
            return _normalize_asset(candidate)
        except Exception:
            continue
    return _emergency_asset()


def _scene_output(scene: Dict[str, Any], index: int, asset: dict) -> dict:
    """Build a scene dict with exactly the manifest keys and safe defaults."""
    out = dict(scene)
    out["scene_id"] = int(scene.get("scene_id") or index + 1)
    span = scene.get("narration_span")
    out["narration_span"] = span if isinstance(span, dict) else {}
    out["visual_type"] = str(scene.get("visual_type") or "illustration")
    out["main_visual_concept"] = str(scene.get("main_visual_concept") or "")
    out["asset"] = asset
    out["camera"] = str(scene.get("camera") or "static")
    out["animation"] = str(scene.get("animation") or "none")
    out["transition"] = str(scene.get("transition") or "cut")
    try:
        out["duration_s"] = float(scene.get("duration_s") or 4.0)
    except (TypeError, ValueError):
        out["duration_s"] = 4.0
    out["fallback_strategy"] = str(
        scene.get("fallback_strategy")
        or ("inline_markup" if asset.get("type") == "markup" else "stock_search")
    )
    out["relevance_assessed"] = True
    return out


def resolve_plan(plan: dict, topic: dict, cache_root: Optional[str] = None) -> dict:
    """Resolve every scene to a licensed asset; never raises."""
    try:
        cache = AssetCache(root=cache_root)
        ledger = LicenseLedger(root=cache_root)
    except Exception:  # pragma: no cover - defensive
        cache, ledger = None, None
    providers = _providers()
    seen: Dict[str, dict] = {}
    scenes_out: List[dict] = []

    plan = plan if isinstance(plan, dict) else {}
    raw_scenes = plan.get("scenes") or []
    if not isinstance(raw_scenes, list):
        raw_scenes = []

    for index, raw in enumerate(raw_scenes):
        scene = raw if isinstance(raw, dict) else {}
        try:
            asset = _resolve_scene(scene, topic, cache, ledger, providers)
        except Exception:
            asset = _emergency_asset()
        # Reuse an identical previously resolved asset (content-addressed).
        digest = str(asset.get("sha256") or "")
        if digest in seen and seen[digest].get("type") == asset.get("type"):
            asset = dict(seen[digest])
        elif digest:
            seen[digest] = dict(asset)
        scene_out = _scene_output(scene, index, asset)
        scenes_out.append(scene_out)
        if cache is not None:
            try:
                cache.record_usage(asset, topic, scene_out["scene_id"])
            except Exception:
                pass

    if ledger is not None:
        try:
            ledger.write()
        except Exception:
            pass

    source = str(
        plan.get("source")
        or (topic.get("source") if isinstance(topic, dict) else "")
        or ""
    )
    return {"topic": topic, "source": source, "scenes": scenes_out}
