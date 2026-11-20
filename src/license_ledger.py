"""License allow-list and attribution helper for visual assets.

Allowed: CC0, Public Domain, CC BY*, CC BY-SA*, Pixabay Content License,
Pexels License, MIT/Own-generated (plus curated ``official press`` assets
from the OfficialMediaProvider allow-list).

Rejected: NC / ND variants, All Rights Reserved, and unknown/blank licenses.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "visual_assets"

ALLOWED_LICENSES = (
    "CC0",
    "Public Domain",
    "CC BY",
    "CC BY-SA",
    "Pixabay Content License",
    "Pexels License",
    "MIT/Own-generated",
    "official press",
)

# NC/ND tokens must appear as standalone hyphen/space/slash delimited words so
# that e.g. "CC BY-NC-SA 4.0" is rejected but "Public Domain" is not.
_RESTRICTED = re.compile(r"(?:^|[-/\s])(nc|nd)(?:$|[-/\s])", re.IGNORECASE)
_HTML_TAG = re.compile(r"<[^>]+>")
_UNKNOWN = {"", "unknown", "none", "n/a", "na", "null", "unspecified"}


class LicenseLedger:
    """Validates licenses and persists the accepted records for auditing."""

    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root) if root else DEFAULT_ROOT
        self.path = self.root / "licenses.json"
        self.records: List[dict] = self._load_records()

    def _load_records(self) -> List[dict]:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            records = data.get("records", []) if isinstance(data, dict) else []
            return records if isinstance(records, list) else []
        except (OSError, ValueError):
            return []

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def normalize(license_value: Any) -> str:
        """Return a canonical allowed license string, or '' when disallowed."""
        if isinstance(license_value, dict):
            license_value = license_value.get("license") or license_value.get("value") or ""
        text = _HTML_TAG.sub(" ", str(license_value or ""))
        text = re.sub(r"\s+", " ", text).strip()
        low = text.lower()
        if low in _UNKNOWN:
            return ""
        if "all rights reserved" in low or "allrightsreserved" in low:
            return ""
        if _RESTRICTED.search(low):
            return ""
        if low.startswith("cc0") or "creative commons zero" in low or low.startswith("cc-zero"):
            return "CC0"
        if low.startswith("public domain") or low.startswith("pdm"):
            return "Public Domain"
        if low.startswith("cc by-sa") or low.startswith("cc-by-sa"):
            return "CC BY-SA"
        if low.startswith("cc by") or low.startswith("cc-by"):
            return "CC BY"
        if low.startswith("pixabay"):
            return "Pixabay Content License"
        if low.startswith("pexels"):
            return "Pexels License"
        if low.startswith("mit") or "own-generated" in low or low.startswith("own generated"):
            return "MIT/Own-generated"
        if low.startswith("official press"):
            return "official press"
        return ""

    def accept(self, record: Any) -> bool:
        """True when the record's license is on the allow-list."""
        if record is None:
            return False
        if isinstance(record, dict):
            return bool(self.normalize(record.get("license")))
        return bool(self.normalize(record))

    def record_asset(self, asset: Dict[str, Any]) -> bool:
        """Validate and remember an accepted asset (deduped by sha256)."""
        if not isinstance(asset, dict) or not self.accept(asset):
            return False
        entry = {
            "sha256": str(asset.get("sha256") or ""),
            "license": self.normalize(asset.get("license")),
            "attribution": str(asset.get("attribution") or ""),
            "source_url": str(asset.get("source_url") or ""),
            "provider": str(asset.get("provider") or ""),
            "type": str(asset.get("type") or ""),
        }
        for existing in self.records:
            if existing.get("sha256") and existing.get("sha256") == entry["sha256"]:
                return True
        self.records.append(entry)
        return True

    def write(self) -> Path:
        """Persist accepted license records to ``licenses.json``."""
        payload = {
            "allowed_licenses": list(ALLOWED_LICENSES),
            "rejected_patterns": ["NC", "ND", "All Rights Reserved", "unknown"],
            "records": self.records,
        }
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        except (OSError, TypeError, ValueError):
            pass
        return self.path

    @staticmethod
    def attribution_line(asset: Dict[str, Any]) -> str:
        """Build a human-readable attribution line for an asset."""
        asset = asset or {}
        parts: List[str] = []
        attribution = str(asset.get("attribution") or "").strip()
        license_name = str(asset.get("license") or "").strip()
        source = str(asset.get("source_url") or "").strip()
        if attribution:
            parts.append(attribution)
        if license_name:
            parts.append("(%s)" % license_name)
        if source:
            parts.append(source)
        return " — ".join(parts)
