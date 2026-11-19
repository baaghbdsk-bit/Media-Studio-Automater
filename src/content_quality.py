"""Guards against generic, low-information AI filler in generated scripts.

These are intentionally narrow: they remove canned promotional/catch-all lines
that add no information, without rewriting genuine content.
"""
import re
from typing import Iterable

SLOP_PHRASES = (
    "follow for",
    "stay curious",
    "watch for the next update",
    "here is what we know so far",
    "the stakes are high for everyone",
    "what actually happened, and why it matters",
    "in today's fast-paced",
    "game-changer",
    "revolutionize",
    "delve into",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def is_slop(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in SLOP_PHRASES)


def clean_text(text: str) -> str:
    """Collapse whitespace and drop canned filler sentences."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    sentences = [
        s.strip()
        for s in _SENTENCE_SPLIT.split(text)
        if s.strip() and not is_slop(s)
    ]
    return " ".join(sentences).strip()


def trim_to_sentences(text: str, max_words: int) -> str:
    """Cut at a sentence boundary so narration never ends mid-thought."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split((text or "").strip()) if s.strip()]
    kept = []
    count = 0
    for sentence in sentences:
        words = len(sentence.split())
        if kept and count + words > max_words:
            break
        kept.append(sentence)
        count += words
    return " ".join(kept).strip()


def unique_by_normalized(items: Iterable[str]) -> set:
    return {re.sub(r"\W+", " ", item.lower()).strip() for item in items}
