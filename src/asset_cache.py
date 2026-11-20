"""Content-addressed, license-aware cache for downloaded visual assets.

Layout (default root is ``<project>/data/visual_assets``)::

    data/visual_assets/
        cache/          # downloaded bytes, named by <sha256><ext>
        assets/         # mirror so manifest local_path "assets/<file>" is real
        cache_index.json
        usage.json      # reuse history (topic + scene_id per asset hash)

The cache deduplicates by sha256. When several equivalent assets are
available, ``select`` prefers an asset not yet used for the same topic, but
only within a relevance gate: a fresh low-relevance asset never beats a more
relevant asset that was already used.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "visual_assets"


def _topic_key(topic: Any) -> str:
    """Stable string identifier for a topic (dict or plain string)."""
    if isinstance(topic, dict):
        for key in ("id", "key", "slug", "title", "topic"):
            value = topic.get(key)
            if value:
                return str(value)
        return json.dumps(topic, sort_keys=True, default=str)[:200]
    return str(topic or "")


class AssetCache:
    """Local cache and reuse-history tracker. All writes are best-effort."""

    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root) if root else DEFAULT_ROOT
        self.cache_dir = self.root / "cache"
        self.assets_dir = self.root / "assets"
        self.usage_path = self.root / "usage.json"
        self.index_path = self.root / "cache_index.json"
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self._index: Dict[str, dict] = self._load_json(self.index_path, {})
        self._usage: List[dict] = self._load_json(self.usage_path, [])

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_json(path: Path, fallback: Any) -> Any:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, type(fallback)) else fallback
        except (OSError, ValueError):
            return fallback

    @staticmethod
    def _save_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True, default=str)
        except (OSError, TypeError, ValueError):
            pass

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """sha256 hex digest of the supplied bytes."""
        return hashlib.sha256(bytes(data)).hexdigest()

    @staticmethod
    def _clean_ext(ext: str) -> str:
        ext = str(ext or "").strip()
        if not ext:
            return ".bin"
        return ext if ext.startswith(".") else "." + ext

    def path_for(self, key: str, ext: str) -> Path:
        """Candidate cache path for a key (callers normally pass a sha256)."""
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(key))[:128] or "asset"
        return self.cache_dir / ("%s%s" % (safe, self._clean_ext(ext)))

    @staticmethod
    def local_path_for(path_or_name: Any) -> str:
        """Convert a cache file/name to the manifest's logical local path."""
        name = Path(str(path_or_name)).name
        return "assets/%s" % name

    def get(self, key: str) -> Optional[bytes]:
        """Return cached bytes for an indexed key (or raw sha256), else None."""
        key = str(key)
        record = self._index.get(key)
        if record and record.get("file"):
            path = self.cache_dir / record["file"]
        else:
            matches = sorted(self.cache_dir.glob("%s.*" % re.escape(key)))
            path = matches[0] if matches else None
        if path is None:
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None

    def put_bytes(self, key: str, data: bytes, ext: str) -> Path:
        """Store *data* content-addressed by sha256; return the cache path."""
        data = bytes(data)
        digest = self.hash_bytes(data)
        ext = self._clean_ext(ext)
        path = self.path_for(digest, ext)
        try:
            if not path.exists():
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            # Mirror into assets/ so the manifest local_path is resolvable.
            self.assets_dir.mkdir(parents=True, exist_ok=True)
            mirror = self.assets_dir / path.name
            if not mirror.exists():
                mirror.write_bytes(data)
        except OSError:
            pass
        self._index[str(key)] = {
            "sha256": digest,
            "file": path.name,
            "ext": ext,
            "local_path": self.local_path_for(path.name),
        }
        self._save_json(self.index_path, self._index)
        return path

    # ------------------------------------------------------------------ #
    # Reuse history / selection
    # ------------------------------------------------------------------ #
    def record_usage(self, asset: Dict[str, Any], topic: Any, scene_id: Any) -> None:
        """Append a usage record to ``usage.json`` for this asset + topic."""
        digest = str((asset or {}).get("sha256") or "") if isinstance(asset, dict) else str(asset)
        record = {
            "asset_hash": digest,
            "topic": _topic_key(topic),
            "scene_id": scene_id,
            "provider": str((asset or {}).get("provider") or "") if isinstance(asset, dict) else "",
            "local_path": str((asset or {}).get("local_path") or "") if isinstance(asset, dict) else "",
            "used_at": time.time(),
        }
        self._usage.append(record)
        self._save_json(self.usage_path, self._usage)

    def was_used(self, asset_hash: str, topic: Any) -> bool:
        """True if this asset hash was already used for the same topic."""
        wanted = _topic_key(topic)
        return any(
            record.get("asset_hash") == asset_hash and record.get("topic") == wanted
            for record in self._usage
        )

    def usage_history(self, topic: Any = None) -> List[dict]:
        """Return usage records, optionally filtered to one topic."""
        if topic is None:
            return list(self._usage)
        wanted = _topic_key(topic)
        return [r for r in self._usage if r.get("topic") == wanted]

    def select(
        self,
        candidates: Iterable[Dict[str, Any]],
        topic: Any,
        score_gate: float = 0.05,
    ) -> Optional[Dict[str, Any]]:
        """Prefer unused candidates without sacrificing meaningful relevance.

        Only candidates within ``score_gate`` of the best relevance score are
        considered "equivalent"; an unused candidate is chosen from that pool.
        """
        pool = [c for c in (candidates or []) if isinstance(c, dict) and c]
        if not pool:
            return None
        best = max(float(c.get("relevance_score") or 0.0) for c in pool)
        equivalent = [c for c in pool if float(c.get("relevance_score") or 0.0) >= best - score_gate]
        fresh = [c for c in equivalent if not self.was_used(str(c.get("sha256") or ""), topic)]
        return (fresh or equivalent)[0]
