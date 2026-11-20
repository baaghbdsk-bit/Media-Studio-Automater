"""Curated official-press media provider (opt-in, small allow-list only).

Disabled unless a scene explicitly requests ``visual_type == official_media``
AND names an allow-listed entity. URLs are verified for reachability before an
asset is returned; failures simply yield ``None``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .base import VisualProvider, make_asset, scene_concept, scene_visual_type

USER_AGENT = "MediaStudioAutomater/1.0 (official press media check; local build)"
TIMEOUT = 8
MAX_BYTES = 12 * 1024 * 1024

# Curated, small allow-list. These are official newsroom/blog image URLs;
# reachability is checked at resolve time, never at import time.
_ALLOWLIST: Dict[str, List[dict]] = {
    "nvidia": [
        {
            "url": "https://nvidianews.nvidia.com/sites/default/files/styles/max_1300x1300/public/nvidia-logo-horizontal.png",
            "attribution": "NVIDIA Newsroom — official press image",
        },
    ],
    "openai": [
        {
            "url": "https://images.openai.com/thumbnails/images-og-image/OPENAI-Brand-Assets.png",
            "attribution": "OpenAI — official brand/press image",
        },
    ],
    "anthropic": [
        {
            "url": "https://www.anthropic.com/images/favicon-32x32.png",
            "attribution": "Anthropic — official press asset",
        },
    ],
    "google": [
        {
            "url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
            "attribution": "Google — official brand asset",
        },
    ],
    "meta": [
        {
            "url": "https://about.fb.com/wp-content/uploads/2021/06/Meta-Logo-Stacked-Blue-Lockup-RGB.png",
            "attribution": "Meta Newsroom — official press image",
        },
    ],
    "microsoft": [
        {
            "url": "https://news.microsoft.com/wp-content/uploads/prod/sites/9/2022/06/microsoft-logo-256.png",
            "attribution": "Microsoft Source — official press image",
        },
    ],
}


def _find_entity(scene: Dict[str, Any], topic: Any) -> Optional[str]:
    parts = [str(scene.get("entity") or scene.get("brand") or scene.get("company") or "")]
    parts.append(scene_concept(scene, topic))
    if isinstance(topic, dict):
        parts.append(" ".join(str(topic.get(key) or "") for key in ("title", "topic", "summary", "description")))
    text = " ".join(parts).lower()
    for entity in _ALLOWLIST:
        if re_word_match(entity, text):
            return entity
    return None


def re_word_match(word: str, text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(word), text))


def _ext_for(url: str, ctype: str) -> str:
    low = (ctype or "").lower()
    for token, ext in (("svg", "svg"), ("jpeg", "jpg"), ("jpg", "jpg"), ("png", "png"), ("webp", "webp")):
        if token in low:
            return ext
    suffix = Path(urlparse(url or "").path).suffix.lower().lstrip(".")
    return suffix if suffix in {"jpg", "jpeg", "png", "webp", "svg"} else "png"


class OfficialMediaProvider(VisualProvider):
    name = "official_media"

    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        kind = scene_visual_type(scene)
        if "official" not in kind:
            return False
        return _find_entity(scene, topic) is not None

    @staticmethod
    def verify_and_fetch(url: str) -> Optional[tuple]:
        """Return (bytes, content_type) for a reachable image URL, else None."""
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                stream=True,
            )
        except Exception:
            return None
        if int(getattr(response, "status_code", 200) or 200) >= 400:
            return None
        ctype = str((getattr(response, "headers", {}) or {}).get("Content-Type") or "")
        if "image" not in ctype.lower():
            return None
        chunks: List[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    return None
                chunks.append(chunk)
        except Exception:
            return None
        data = b"".join(chunks)
        return (data, ctype) if data else None

    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        entity = _find_entity(scene, topic)
        if not entity:
            return None
        for entry in _ALLOWLIST.get(entity, []):
            url = str(entry.get("url") or "")
            if not url:
                continue
            fetched = self.verify_and_fetch(url)
            if not fetched:
                continue
            try:
                data, ctype = fetched
                digest = cache.hash_bytes(data)
                path = cache.put_bytes(url, data, _ext_for(url, ctype))
                asset = make_asset(
                    self.name,
                    "image",
                    local_path=cache.local_path_for(path),
                    source_url=url,
                    license="official press",
                    attribution=str(entry.get("attribution") or "%s official press" % entity),
                    sha256=digest,
                    relevance_score=0.95,
                )
                if ledger.accept(asset):
                    ledger.record_asset(asset)
                    return asset
            except Exception:
                continue
        return None
