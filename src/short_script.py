"""Purpose-built composer for 45-55 second YouTube Shorts scripts.

This is not a truncation of a longer script. It builds a seven-beat short-form
narration from a single topic idea, entirely deterministically: no network,
no randomness, and no API calls.

Design guarantees:

* Every emitted sentence is a *complete* sentence. Text is never cut
  mid-word or mid-clause; an oversized fragment is dropped, not trimmed.
* A normalized-sentence set and an opener set prevent the same clause,
  sentence, or subject-verb phrase from appearing in two beats.
* Word count is tuned only by adding or removing whole sentences.
"""
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow both `import src.short_script` (package) and `python src/short_script.py`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.content_quality import clean_text, is_slop, SLOP_PHRASES

_BEAT_ORDER: List[str] = [
    "hook", "stake", "context", "mechanism", "aha", "payoff", "loop",
]

_TARGET_S: Dict[str, float] = {
    "hook": 2.5,
    "stake": 5.0,
    "context": 7.0,
    "mechanism": 11.0,
    "aha": 8.0,
    "payoff": 9.0,
    "loop": 5.0,
}

_BEAT_META: Dict[str, tuple] = {
    "hook": ("The Hook", "the question"),
    "stake": ("Why It Matters", "the cost"),
    "context": ("The Setup", "the setup"),
    "mechanism": ("How It Works", "the mechanism"),
    "aha": ("The Surprise", "the surprise"),
    "payoff": ("Your Move", "your move"),
    "loop": ("The Loop", "one thing"),
}

_LINE_FALLBACKS: Dict[str, str] = {
    "hook": "the real question",
    "stake": "why it matters",
    "context": "the setup",
    "mechanism": "step by step",
    "aha": "the surprise",
    "payoff": "your move",
    "loop": "one last thought",
}

_WPM = 145
_TARGET_WORDS = 110
_MAX_WORDS = 120
_MAX_SENTENCE_WORDS = 20

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_SPLIT = re.compile(
    r"\s+(?:while|whereas|because|but|and|that|which|although|though|since|so)\s+",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_REPEATED_WORD = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)

# Words that may never end a sentence (dangling conjunction/article/verb).
_DANGLING = {
    "while", "because", "and", "but", "that", "which", "although", "though",
    "since", "so", "with", "for", "of", "to", "in", "on", "at", "by", "as",
    "or", "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "its", "their", "his", "her", "our", "your", "from", "into", "than", "then",
}

# Distinct whole recap sentences used only to reach the word-count target.
_EXTRA_SENTENCES: List[str] = [
    "One small detail explains most of the confusion.",
    "The tradeoff is easier to spot than you think.",
    "That difference shows up in everyday results.",
    "Both sides make sense once you know the context.",
    "The core idea is simpler than it sounds.",
    "You can spot it once you know what to look for.",
    "It's a practical distinction, not a theoretical one.",
    "The rest follows from that simple starting point.",
    "Each side has its own place in the workflow.",
    "This is the detail that changes the outcome.",
    "The pattern shows up again and again.",
    "It helps to see the two sides side by side.",
    "That framing makes the whole thing clearer.",
    "The takeaway is easy to carry with you.",
]

# Last-resort sentences, each with a unique opener, for degenerate inputs.
_FALLBACK_SENTENCES: List[str] = [
    "Here's the part worth keeping.",
    "It comes down to one clear idea.",
    "The key detail is worth a second look.",
    "That framing makes the picture clearer.",
    "There's a simple way to see it.",
    "The core point is easy to miss.",
    "This is the bit that matters most.",
]

_TITLE_STOPWORDS = {
    "why", "what", "how", "when", "where", "who", "which", "the", "a", "an",
    "is", "are", "do", "does", "did", "for", "with", "to", "of", "and", "in",
    "on", "at", "as", "by", "from", "your", "you", "it", "this", "that",
}


def _clean(value: Any) -> str:
    """Return cleaned text for any topic value, using the shared quality guard."""
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    return clean_text(value)


def _sentences(text: str) -> List[str]:
    """Split text into complete, stripped sentences."""
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]


def _norm(text: str) -> str:
    """Normalize a sentence for duplicate detection."""
    return " ".join(_WORD_RE.findall(text.lower()))


def _opener(text: str) -> str:
    """Return the first three normalized words (a subject-verb signature)."""
    return " ".join(_norm(text).split()[:3])


def _complete_sentence(text: Any, max_words: int = _MAX_SENTENCE_WORDS) -> str:
    """Return one complete sentence, or an empty string.

    The first sentence of ``text`` is used. If it exceeds ``max_words`` it is
    dropped entirely -- it is never cut short. Terminal punctuation is added
    only when a complete sentence is missing it.
    """
    sentence = _first(_sentences(_clean(text)))
    if not sentence:
        return ""
    if len(sentence.split()) > max_words:
        return ""
    if sentence[-1] not in ".!?":
        sentence += "."
    if _norm(sentence).split()[-1] in _DANGLING:
        return ""
    if is_slop(sentence):
        return ""
    if _REPEATED_WORD.search(sentence):
        return ""
    return sentence


def _frag(text: Any, max_words: int = _MAX_SENTENCE_WORDS) -> str:
    """Return a complete sentence, or an empty string.

    Text is never cut mid-word or mid-clause. If the first sentence does not
    fit within ``max_words`` whole words, the fragment is dropped entirely.
    """
    return _complete_sentence(text, max_words)


def _first(items: List[str]) -> str:
    """Return the first item of a list, or an empty string."""
    return items[0] if items else ""


def _clauses(text: Any) -> List[str]:
    """Split source text into complete clause-level sentences.

    Splitting on subordinating and coordinating conjunctions yields several
    distinct, self-contained facts from a single long sentence (for example a
    "X while Y" sentence produces two clauses). Oversized or dangling pieces
    are discarded rather than truncated.
    """
    result: List[str] = []
    for sentence in _sentences(_clean(text)):
        for piece in _CLAUSE_SPLIT.split(sentence):
            piece = piece.strip().rstrip(".,;:!?").strip()
            if not piece:
                continue
            words = piece.split()
            if len(words) > _MAX_SENTENCE_WORDS:
                continue
            if words[-1].lower() in _DANGLING:
                continue
            piece = piece[:1].upper() + piece[1:] + "."
            if is_slop(piece) or _REPEATED_WORD.search(piece):
                continue
            result.append(piece)
    return result


def _embedded(clause: str) -> str:
    """Return a complete clause as a lowercased, unpunctuated mid-sentence bit."""
    if not clause:
        return ""
    body = clause[:-1] if clause.endswith((".", "!", "?")) else clause
    return body[:1].lower() + body[1:]


def _topic_text(topic: Dict[str, Any]) -> Dict[str, str]:
    """Extract and clean topic fields.

    For NEWS topics only ``title`` and ``summary`` are admitted as factual
    grounding; problem/solution style fields are deliberately ignored so that
    no claim is invented.
    """
    pillar = str(topic.get("pillar", "") or "").strip().upper()
    fields = {
        "title": _clean(topic.get("title", "")),
        "summary": _clean(topic.get("summary", "")),
    }
    optional = ("hook", "analogy", "problem", "solution", "takeaway", "pro_tip")
    for key in optional:
        fields[key] = "" if pillar == "NEWS" else _clean(topic.get(key, ""))
    fields["pillar"] = pillar
    return fields


class _Used:
    """Tracks normalized sentences and openers to guarantee distinct beats."""

    def __init__(self) -> None:
        self.sentences: set = set()
        self.openers: set = set()

    def take(self, candidate: Optional[str]) -> Optional[str]:
        """Accept a candidate only if it is valid and not a duplicate."""
        if not candidate:
            return None
        sentence = candidate.strip()
        if len(sentence.split()) > _MAX_SENTENCE_WORDS:
            return None
        if not sentence.endswith((".", "!", "?")):
            return None
        if sentence.lower().split()[-1].strip(".!?") in _DANGLING:
            return None
        if is_slop(sentence):
            return None
        if _REPEATED_WORD.search(sentence):
            return None
        normalized, opener = _norm(sentence), _opener(sentence)
        if normalized in self.sentences or opener in self.openers:
            return None
        self.sentences.add(normalized)
        self.openers.add(opener)
        return sentence


def _pick(used: _Used, candidates: List[str]) -> str:
    """Return the first fresh candidate, or the first fresh fallback."""
    for candidate in candidates:
        accepted = used.take(candidate)
        if accepted:
            return accepted
    for candidate in _FALLBACK_SENTENCES:
        accepted = used.take(candidate)
        if accepted:
            return accepted
    return "Here's the key idea."  # pragma: no cover - only if bank exhausted


def _build_banks(fields: Dict[str, str]) -> tuple:
    """Build one ordered candidate bank per beat.

    Real topic content is preferred when present. For sparse topics (title and
    summary only) each beat draws a different angle from the available clauses
    and uses a different connector and sentence opening.
    """
    title = fields["title"]
    summary = fields["summary"]
    title_base = title.rstrip(".,!? ")
    title_q = title_base if title_base.endswith("?") else title_base + "?"
    clauses = _clauses(summary)
    c0 = _embedded(clauses[0]) if clauses else ""
    c1 = _embedded(clauses[1]) if len(clauses) > 1 else ""
    has_summary = bool(summary)

    hook: List[str] = []
    hook_question = next((s for s in _sentences(fields["hook"]) if "?" in s), "")
    if hook_question:
        hook.append(_complete_sentence(hook_question))
    hook.append(f"Here's the question you should be asking: {title_q}")
    hook.append(f"Here's the question: {title_q}")
    hook.append(title_q)
    hook.append(f"Let's start with this: {title_q}")

    stake: List[str] = []
    if fields["problem"]:
        stake.append(_complete_sentence(fields["problem"]))
    if has_summary:
        stake.append("That difference decides which option actually fits the work you do.")
        stake.append("Get this wrong and the tradeoff shows up fast in practice.")
    else:
        stake.append(f"Here's why it matters: {title_base}")
    stake.append("Miss it and the gap shows up in real results.")

    context: List[str] = []
    if fields["analogy"]:
        context.append(_complete_sentence(fields["analogy"]))
    if c1:
        context.append(f"On the other side of that same story, {c1}.")
    if has_summary:
        context.append(_complete_sentence(summary))
    context.append(f"Here's the setup: {title_base}" if title_base else "")
    context.append("In plain terms, you're weighing two different approaches.")

    mechanism: List[str] = []
    if fields["solution"]:
        mechanism.append(_complete_sentence(fields["solution"]))
    if c0:
        mechanism.append(f"The mechanism is simple: {c0}.")
        mechanism.append(f"It starts with {c0}.")
    mechanism.append("It works through one repeatable step.")

    aha: List[str] = []
    if fields["takeaway"]:
        aha.append(_complete_sentence(fields["takeaway"]))
    aha.append("Here's the surprise: that one small detail changes the whole result.")
    aha.append("The surprising part is how that single step adds up.")
    aha.append("What catches people off guard is the simple math behind it.")

    payoff: List[str] = []
    if fields["pro_tip"]:
        payoff.append(_complete_sentence(fields["pro_tip"]))
    payoff.append("Pick the option that fits the work you actually do every day.")
    payoff.append("Match your workload to the tool built for that job.")
    payoff.append("Choose based on the work rather than the noise.")

    loop: List[str] = [
        "So which side does your own work fall on?",
        "Which option fits what you're building?",
        "So what does your own setup look like?",
    ]

    return [hook, stake, context, mechanism, aha, payoff, loop], title_base


def _short_line(sentence: str, fallback: str) -> str:
    """Derive a short on-screen line from a sentence without dangling words."""
    words = [w for w in sentence.split()[:5]]
    while words and words[-1].lower().strip(".!?") in _DANGLING:
        words.pop()
    return " ".join(words).rstrip(".,!?;:") if words else fallback


def build_short_script(topic: dict) -> dict:
    """Compose a deterministic 45-55 second YouTube Shorts script.

    Args:
        topic: May contain ``title``, ``summary``, ``hook``, ``analogy``,
            ``problem``, ``solution``, ``takeaway``, ``pro_tip``, ``pillar``,
            ``entities``, ``acts`` and ``audience``. Missing keys are tolerated.

    Returns:
        A dict with exactly ``title``, ``beats``, ``narration``, ``words`` and
        ``qa``. ``beats`` holds exactly seven ordered beat dictionaries.
    """
    topic = topic if isinstance(topic, dict) else {}
    fields = _topic_text(topic)
    banks, title_base = _build_banks(fields)
    used = _Used()

    # One fresh sentence per beat: no clause is ever reused across beats.
    per_beat: List[List[str]] = [
        [_pick(used, bank)] for bank in banks
    ]

    def total() -> int:
        return sum(len(s.split()) for beat in per_beat for s in beat)

    # Reach the target using whole sentences only, spread across the middle
    # beats so no single beat becomes a wall of text.
    rotation = [1, 2, 3, 4, 5]
    added = 0
    for candidate in _EXTRA_SENTENCES:
        if total() >= _TARGET_WORDS:
            break
        accepted = used.take(candidate)
        if not accepted:
            continue
        if total() + len(accepted.split()) > _MAX_WORDS - 2:
            used.sentences.discard(_norm(accepted))
            used.openers.discard(_opener(accepted))
            continue
        per_beat[rotation[added % len(rotation)]].append(accepted)
        added += 1

    # If the source text alone was oversized, remove whole sentences (never
    # truncate) from the end of the fullest beats until within range.
    while total() > _MAX_WORDS:
        candidates = [i for i, beat in enumerate(per_beat) if len(beat) > 1]
        if not candidates:
            break
        idx = max(candidates, key=lambda i: len(" ".join(per_beat[i]).split()))
        per_beat[idx].pop()

    narrations = [" ".join(beat) for beat in per_beat]
    beats: List[Dict[str, Any]] = []
    for i, beat_id in enumerate(_BEAT_ORDER):
        label, focus = _BEAT_META[beat_id]
        beats.append({
            "id": beat_id,
            "label": label,
            "focus_word": focus,
            "lines": [focus.title(), _short_line(per_beat[i][0], _LINE_FALLBACKS[beat_id])],
            "narration": narrations[i],
            "target_s": _TARGET_S[beat_id],
        })

    narration = " ".join(narrations)
    words = narration.split()
    word_count = len(words)
    all_sentences = [s for beat in per_beat for s in beat]

    flags: List[str] = []
    if not (100 <= word_count <= 120):
        flags.append("word_count_out_of_range")
    if is_slop(narration):
        flags.append("slop_detected")
    if any(len(s.split()) > _MAX_SENTENCE_WORDS for s in all_sentences):
        flags.append("long_sentence")
    if any(not s.endswith((".", "!", "?")) for s in all_sentences):
        flags.append("unterminated_sentence")
    if len({_norm(s) for s in all_sentences}) != len(all_sentences):
        flags.append("repeated_sentence")
    if len({_opener(s) for s in all_sentences}) != len(all_sentences):
        flags.append("repeated_opener")
    if len(beats) != 7:
        flags.append("beat_count_mismatch")

    title = fields["title"] or title_base or fields["summary"][:80].strip() or "Quick Breakdown"
    title = clean_text(title) or "Quick Breakdown"

    return {
        "title": title,
        "beats": beats,
        "narration": narration,
        "words": words,
        "qa": {
            "word_count": word_count,
            "estimated_seconds_at_145wpm": round(word_count / _WPM * 60, 1),
            "flags": flags,
        },
    }


if __name__ == "__main__":
    sample_topic = {
        "title": "Why your focus feels impossible",
        "summary": "Attention is shaped by the room you work in, not just willpower.",
        "hook": "What if your attention span isn't the problem?",
        "analogy": "It's like trying to bail water with a sieve.",
        "problem": "You're fighting your own environment.",
        "solution": "Redesign the room before you redesign your willpower.",
        "takeaway": "Environment beats intention every time.",
        "pro_tip": "Move your phone to another room for one hour.",
        "pillar": "EDUCATION",
        "entities": ["attention", "environment"],
        "acts": ["reduce friction", "protect focus"],
        "audience": "busy creators",
    }

    result = build_short_script(sample_topic)
    for beat in result["beats"]:
        print(f"[{beat['id']}] ({beat['target_s']}s) {beat['label']}")
        print(f"  focus: {beat['focus_word']} | lines: {beat['lines']}")
        print(f"  {beat['narration']}")
    print("\nFull narration:\n" + result["narration"])
    print("QA: " + str(result["qa"]))

    assert 100 <= result["qa"]["word_count"] <= 120, "word count must be 100-120"
    assert len(result["beats"]) == 7, "exactly seven beats required"
    assert result["qa"]["flags"] == [], "QA flags must be empty"
    print("Self-test passed.")
