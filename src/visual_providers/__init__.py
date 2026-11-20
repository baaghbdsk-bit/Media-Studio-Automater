"""Modular, license-aware visual asset providers."""

from .base import ASSET_KEYS, ResolvedAsset, VisualProvider, is_valid_asset, make_asset

try:  # package import
    from ..asset_cache import AssetCache
    from ..license_ledger import LicenseLedger
except Exception:  # pragma: no cover - flat import fallback
    from asset_cache import AssetCache  # type: ignore
    from license_ledger import LicenseLedger  # type: ignore
from .diagram_provider import DiagramProvider
from .fallback_provider import FallbackProvider
from .illustration_provider import IllustrationProvider
from .official_media_provider import OfficialMediaProvider
from .orchestrator import resolve_plan
from .stock_provider import StockProvider
from .ui_mock_provider import UiMockProvider

__all__ = [
    "ASSET_KEYS",
    "ResolvedAsset",
    "VisualProvider",
    "is_valid_asset",
    "make_asset",
    "AssetCache",
    "LicenseLedger",
    "StockProvider",
    "OfficialMediaProvider",
    "IllustrationProvider",
    "DiagramProvider",
    "UiMockProvider",
    "FallbackProvider",
    "resolve_plan",
]
