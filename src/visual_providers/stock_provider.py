"""Free-license stock image provider (Wikimedia Commons, Openverse, Pixabay).

No API keys are required for Wikimedia Commons or Openverse; Pixabay is only
queried when ``PIXABAY_API_KEY`` is present in the environment. Every API
failure is isolated: the next source is tried, and ``None`` is returned when
all sources fail so the orchestrator can fall back to generated markup.

Images are always downloaded and served from the local cache -- never
hotlinked. User-Agent headers are sent politely and downloads are capped.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .base import VisualProvider, make_asset, scene_visual_type

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
PIXABAY_API = "https://pixabay.com/api/"

USER_AGENT = (
    "MediaStudioAutomater/1.0 "
    "(https://github.com/baaghbdsk-bit/Media-Studio-Automater; license-aware visual assets)"
)
TIMEOUT = 20
MAX_BYTES = 12 * 1024 * 1024  # 12 MB per asset

# Content-safety filter: prefer object/scene imagery, never identifiable people.
_PERSON_TERMS = (
    "portrait", "woman", "man ", " girl", " boy", "face", "person", "people",
    "celebrity", "actor", "actress", "model", "sexy", "lingerie", "nude",
    "swimwear", "selfie", "wedding", "baby", "child",
)


def _safe_title(title: Any) -> bool:
    text = " " + str(title or "").lower() + " "
    return not any(term in text for term in _PERSON_TERMS)

_SUPPORTED_TYPES = {
    "stock_image", "stock_footage", "stock", "stock_photo", "photo",
    "photograph", "image", "footage", "media", "picture", "real_image",
}

_OPENVERSE_LICENSE = {
    "cc0": "CC0",
    "pdm": "Public Domain",
    "by": "CC BY 4.0",
    "by-sa": "CC BY-SA 4.0",
}


def _strip_tags(text: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()


def _get(url: str, **kwargs: Any):
    """GET with a polite User-Agent, timeout and 429/5xx backoff."""
    headers = dict(kwargs.pop("headers", {}) or {})
    headers.setdefault("User-Agent", USER_AGENT)
    kwargs.setdefault("timeout", TIMEOUT)
    last = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, **kwargs)
            if int(getattr(response, "status_code", 200) or 200) not in (429, 500, 502, 503, 504):
                return response
            last = response
        except requests.RequestException as exc:
            last = exc
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))
    if last is not None:
        return last
    return requests.get(url, headers=headers, **kwargs)


def _ok(response: Any) -> bool:
    return int(getattr(response, "status_code", 200) or 200) < 400


def _meta_value(metadata: Dict[str, Any], key: str) -> str:
    value = metadata.get(key) if isinstance(metadata, dict) else None
    if isinstance(value, dict):
        return str(value.get("value") or "")
    return str(value or "")


def _ext_for(ctype: str, url: str) -> str:
    low = (ctype or "").lower()
    for token, ext in (
        ("svg", "svg"), ("jpeg", "jpg"), ("jpg", "jpg"), ("png", "png"),
        ("webp", "webp"), ("gif", "gif"), ("avif", "avif"),
    ):
        if token in low:
            return ext
    suffix = Path(urlparse(url or "").path).suffix.lower().lstrip(".")
    return suffix if suffix in {"jpg", "jpeg", "png", "webp", "gif", "svg", "avif"} else "jpg"


class StockProvider(VisualProvider):
    name = "stock"

    def supports(self, scene: Dict[str, Any], topic: Any) -> bool:
        kind = scene_visual_type(scene)
        return kind in _SUPPORTED_TYPES or "stock" in kind

    _CANONICAL_QUERY = {
        "gpu": "graphics card", "gpus": "graphics card",
        "cpu": "computer processor", "cpus": "computer processor",
        "ai": "artificial intelligence", "agent": "software agent",
        "agents": "software agent", "benchmark": "performance chart",
        "benchmarks": "performance chart", "model": "machine learning model",
        "models": "machine learning model", "news": "technology news",
    }

    _QUERY_STOP = {
        "beat", "beats", "run", "runs", "running", "show", "shows", "showing",
        "happen", "happening", "during", "thing", "things", "question", "asking",
        "should", "pick", "move", "setup", "actually", "decides", "fits", "option",
        "options", "building", "cost", "difference",
    }

    @staticmethod
    def build_query(scene: Dict[str, Any], topic: Any) -> str:
        keywords = (scene or {}).get("search_keywords")
        parts: List[str] = []
        if isinstance(keywords, list):
            for raw in keywords:
                word = re.sub(r"[^A-Za-z0-9]+", "", str(raw or "")).lower()
                if len(word) < 3 or word in StockProvider._QUERY_STOP:
                    continue
                term = StockProvider._CANONICAL_QUERY.get(word, word)
                if term not in parts:
                    parts.append(term)
                if len(parts) >= 1:
                    break
        if not parts:
            parts = [str((scene or {}).get("main_visual_concept") or "technology").split()[0]]
        text = " ".join(parts)
        return re.sub(r"\s+", " ", text).strip()[:70]

    # ------------------------------------------------------------------ #
    # Source searches -> candidate dicts (no downloads yet)
    # ------------------------------------------------------------------ #
    def search_wikimedia(self, query: str) -> List[dict]:
        params = {
            "action": "query", "generator": "search", "gsrsearch": query,
            "gsrnamespace": 6, "gsrlimit": 8, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 1024, "format": "json",
        }
        response = _get(WIKIMEDIA_API, params=params)
        if not _ok(response):
            return []
        data = response.json()
        pages = (data.get("query") or {}).get("pages") or {}
        candidates: List[dict] = []
        for page in pages.values():
            if not isinstance(page, dict):
                continue
            info = ((page.get("imageinfo") or [{}])[0]) or {}
            metadata = info.get("extmetadata") or {}
            license_raw = (
                _meta_value(metadata, "LicenseShortName")
                or _meta_value(metadata, "LicenseUrl")
            )
            artist = _strip_tags(_meta_value(metadata, "Artist")) or "Wikimedia Commons contributor"
            source = info.get("thumburl") or info.get("url") or ""
            page_url = info.get("descriptionurl") or info.get("descriptionshorturl") or ""
            if not source or not _safe_title(page.get("title")):
                continue
            candidates.append({
                "source_url": source,
                "license": license_raw,
                "attribution": "%s / Wikimedia Commons%s" % (
                    artist, " (%s)" % page_url if page_url else ""
                ),
                "title": str(page.get("title") or ""),
            })
        return candidates

    def search_openverse(self, query: str) -> List[dict]:
        response = _get(OPENVERSE_API, params={"q": query, "page_size": 8})
        if not _ok(response):
            return []
        data = response.json()
        candidates: List[dict] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            raw_license = str(item.get("license") or "").strip().lower()
            version = str(item.get("license_version") or "").strip()
            license_name = _OPENVERSE_LICENSE.get(raw_license, str(item.get("license") or ""))
            creator = _strip_tags(item.get("creator") or "") or "Openverse contributor"
            source = item.get("thumbnail") or item.get("url") or ""
            if not source or not _safe_title(item.get("title")):
                continue
            attribution = "%s / Openverse" % creator
            if version:
                attribution += " (%s %s)" % (license_name, version)
            candidates.append({
                "source_url": source,
                "license": license_name,
                "attribution": attribution,
                "title": str(item.get("title") or ""),
            })
        return candidates

    def search_pixabay(self, query: str) -> List[dict]:
        api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
        if not api_key:
            return []
        response = _get(
            PIXABAY_API,
            params={"key": api_key, "q": query, "image_type": "photo", "per_page": 8},
        )
        if not _ok(response):
            return []
        candidates: List[dict] = []
        for hit in (response.json().get("hits") or []):
            source = hit.get("webformatURL") or hit.get("previewURL") or hit.get("imageURL") or ""
            if not source or not _safe_title(hit.get("tags")):
                continue
            candidates.append({
                "source_url": source,
                "license": "Pixabay Content License",
                "attribution": "%s / Pixabay" % (hit.get("user") or "Pixabay contributor"),
                "title": str(hit.get("tags") or ""),
            })
        return candidates

    # ------------------------------------------------------------------ #
    # Download + resolution
    # ------------------------------------------------------------------ #
    @staticmethod
    def download(url: str) -> Optional[tuple]:
        """Return (bytes, content_type) or None; enforce type + size caps."""
        response = _get(url, stream=True)
        if not _ok(response):
            return None
        ctype = str((getattr(response, "headers", {}) or {}).get("Content-Type") or "")
        if "image" not in ctype.lower():
            return None
        chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_content(8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_BYTES:
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
        return (data, ctype) if data else None

    _GENERIC_QUERY_WORDS = {
        "computer", "technology", "software", "performance", "machine",
        "learning", "news", "digital", "modern", "system", "systems",
    }

    @staticmethod
    def _score(candidate: dict, query: str) -> float:
        title = str(candidate.get("title") or "").lower()
        words = {w for w in re.split(r"\W+", query.lower()) if len(w) > 3}
        overlap = sum(1 for word in words if word in title)
        distinctive = {w for w in words if w not in StockProvider._GENERIC_QUERY_WORDS}
        strong_hit = sum(1 for word in distinctive if word in title)
        if overlap == 0 or (strong_hit == 0 and overlap < 2):
            return 0.0
        return round(0.62 + min(0.33, 0.08 * (strong_hit or overlap)), 3)

    def resolve(self, scene: Dict[str, Any], topic: Any, cache: Any, ledger: Any) -> Optional[dict]:
        query = self.build_query(scene, topic)
        if not query:
            return None
        searches = [self.search_wikimedia, self.search_openverse]
        if os.environ.get("PIXABAY_API_KEY", "").strip():
            searches.append(self.search_pixabay)

        for search in searches:
            try:
                candidates = search(query) or []
            except Exception:
                continue
            accepted: List[dict] = []
            for candidate in candidates:
                try:
                    if not isinstance(candidate, dict) or not ledger.accept(candidate):
                        continue
                    downloaded = self.download(candidate.get("source_url") or "")
                    if not downloaded:
                        continue
                    data, ctype = downloaded
                    digest = cache.hash_bytes(data)
                    ext = _ext_for(ctype, candidate.get("source_url") or "")
                    path = cache.put_bytes(candidate.get("source_url") or digest, data, ext)
                    asset_type = "video" if ext in {"mp4", "webm", "mov"} else "image"
                    asset = make_asset(
                        self.name,
                        asset_type,
                        local_path=cache.local_path_for(path),
                        source_url=str(candidate.get("source_url") or ""),
                        license=ledger.normalize(candidate.get("license")),
                        attribution=_strip_tags(candidate.get("attribution")),
                        sha256=digest,
                        relevance_score=self._score(candidate, query),
                    )
                    if ledger.accept(asset):
                        accepted.append(asset)
                except Exception:
                    continue
            accepted = [
                asset for asset in accepted
                if float(asset.get("relevance_score") or 0.0) >= 0.62
            ]
            try:
                chosen = cache.select(accepted, topic, score_gate=0.05)
            except Exception:
                chosen = accepted[0] if accepted else None
            if chosen:
                try:
                    ledger.record_asset(chosen)
                except Exception:
                    pass
                return chosen
        return None
