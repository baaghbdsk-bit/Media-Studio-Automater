"""Topic fingerprinting and 30-day duplicate detection.

The channel publishes several videos a day, so exact-title matching is not
enough.  This module normalises titles, extracts a stable "series" key and
compares candidates against recent history so that near-duplicates such as
"FlashAttention" / "FlashAttention-3" / "How FlashAttention works" are treated
as the same story.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_WINDOW_DAYS = 30
DEFAULT_SIMILARITY = 0.62

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "how", "what", "why", "when",
    "where", "who", "which", "do", "does", "did", "can", "could", "should",
    "would", "will", "your", "you", "we", "our", "they", "their", "explained",
    "explainer", "guide", "intro", "introduction", "basics", "simply", "really",
    "actually", "complete", "full", "deep", "dive", "part", "vs", "versus",
}

SERIES_ALIASES: Dict[str, str] = {
    "mixture of experts": "mixture-of-experts",
    "mixture-of-experts": "mixture-of-experts",
    "moe": "mixture-of-experts",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "rag": "rag",
    "flashattention": "flashattention",
    "flash attention": "flashattention",
    "pagedattention": "paged-attention",
    "paged attention": "paged-attention",
    "kv cache": "kv-cache",
    "key value cache": "kv-cache",
    "key-value cache": "kv-cache",
    "speculative decoding": "speculative-decoding",
    "vector embedding": "embeddings",
    "vector embeddings": "embeddings",
    "embeddings": "embeddings",
    "quantization": "quantization",
    "quantisation": "quantization",
    "lora": "lora",
    "qlora": "lora",
    "low rank adaptation": "lora",
    "low-rank adaptation": "lora",
    "zero trust": "zero-trust",
    "supply chain": "supply-chain",
    "merkle tree": "merkle-tree",
    "merkle trees": "merkle-tree",
    "sql injection": "sql-injection",
    "race condition": "race-condition",
    "load balancer": "load-balancing",
    "load balancing": "load-balancing",
    "message queue": "message-queue",
    "database index": "database-index",
    "caching": "caching",
    "cache": "caching",
    "http": "http",
    "https": "http",
    "api": "api",
    "apis": "api",
    "gps": "gps",
    "encryption": "encryption",
    "phishing": "phishing",
    "passkey": "passkeys",
    "passkeys": "passkeys",
    "two factor": "passkeys",
    "2fa": "passkeys",
    "system design": "system-design",
    "observability": "observability",
    "tech debt": "tech-debt",
    "technical debt": "tech-debt",
    "on call": "on-call",
    "on-call": "on-call",
    "latency": "latency-throughput",
    "throughput": "latency-throughput",
    "build vs buy": "build-vs-buy",
}


def normalize(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _singular(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokens(text: str) -> List[str]:
    out = []
    for word in normalize(text).split():
        if word in STOPWORDS or len(word) <= 2:
            continue
        out.append(_singular(word))
    return out


def fingerprint(text: str) -> str:
    return " ".join(sorted(set(tokens(text))))


def series_key(title: str, entities: Optional[Iterable[str]] = None,
               explicit: Optional[str] = None) -> str:
    if explicit:
        return normalize(explicit).replace(" ", "-")
    blob = normalize(title)
    if entities:
        blob = f"{blob} {' '.join(normalize(e) for e in entities)}"
    for phrase, key in SERIES_ALIASES.items():
        if re.search(rf"\b{re.escape(phrase)}\b", blob):
            return key
    return ""


def similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    ta, tb = set(tokens(a)), set(tokens(b))
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    sequence = SequenceMatcher(None, na, nb).ratio()
    containment = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
    return max(jaccard, sequence * 0.92, containment * 0.78)


def parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %I:%M %p", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if "T" in fmt else text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def is_within(entry: Dict[str, Any], days: int = DEFAULT_WINDOW_DAYS,
              now: Optional[datetime] = None) -> bool:
    stamp = parse_time(entry.get("time"))
    if stamp is None:
        # Legacy entries have no timestamp; treat them as recent so the first
        # post-migration month cannot repeat old stories.
        return True
    now = now or datetime.utcnow()
    return stamp >= now - timedelta(days=days)


def is_duplicate(candidate: Dict[str, Any],
                 entries: List[Dict[str, Any]],
                 days: int = DEFAULT_WINDOW_DAYS,
                 threshold: float = DEFAULT_SIMILARITY,
                 now: Optional[datetime] = None) -> bool:
    title = str(candidate.get("title") or "")
    if not title:
        return True
    cand_series = str(candidate.get("series") or "")
    for entry in entries:
        if not is_within(entry, days, now):
            continue
        old_title = str(entry.get("title") or "")
        if not old_title:
            continue
        if cand_series and str(entry.get("series") or "") == cand_series:
            return True
        if similarity(title, old_title) >= threshold:
            return True
    return False


def recent(entries: List[Dict[str, Any]], days: int = DEFAULT_WINDOW_DAYS,
           now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    return [e for e in entries if is_within(e, days, now)]


def recent_titles(entries: List[Dict[str, Any]], days: int = DEFAULT_WINDOW_DAYS,
                  now: Optional[datetime] = None) -> List[str]:
    out: List[str] = []
    for entry in recent(entries, days, now):
        title = str(entry.get("title") or "").strip()
        if title and title not in out:
            out.append(title)
    return out


def recent_series(entries: List[Dict[str, Any]], days: int = DEFAULT_WINDOW_DAYS,
                  now: Optional[datetime] = None) -> List[str]:
    out: List[str] = []
    for entry in recent(entries, days, now):
        key = str(entry.get("series") or "").strip()
        if key and key not in out:
            out.append(key)
    return out
