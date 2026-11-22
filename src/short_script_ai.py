"""Gemini-powered seven-beat Shorts script writer.

The deterministic composer in ``short_script.py`` is the safety net; this
module is the primary path when a Gemini API key is available. It asks the
model for a purpose-built 45-55s short script (never a truncated long-form
script), validates the result strictly, and returns ``None`` so callers can
fall back safely.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.content_quality import is_slop
from src.short_config import (
    BEAT_IDS as _BEAT_IDS,
    LABELS as _LABELS,
    TARGET_S as _TARGET_S,
    SHORT_BEATS,
    SHORT_WORD_MIN,
    SHORT_WORD_MAX,
    SHORT_WPM,
)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _prompt(topic: Dict[str, Any]) -> str:
    payload = {
        "title": str(topic.get("title") or ""),
        "summary": str(topic.get("summary") or ""),
        "hook": str(topic.get("hook") or ""),
        "pillar": str(topic.get("pillar") or ""),
        "entities": topic.get("entities") or [],
    }
    news = str(payload["pillar"]).upper() == "NEWS"
    grounding = (
        "Use ONLY the title and summary as facts. Do not invent claims, motives, "
        "numbers, or outcomes." if news else
        "Use the topic fields as factual anchors. Explain one mechanism clearly."
    )
    return f"""<role>
You are a person explaining a tech idea to a friend over coffee. You are NOT writing a script, an article, or a narration. Say words the way you would actually say them out loud.
</role>

<task>
Rewrite the topic into 12 spoken beats, 215-260 words total (~90-105s spoken). Each beat is 2-3 spoken sentences of 10-18 words. Tell a complete story: set up the problem, build the mechanism in two steps, ground it in a concrete example, reveal the surprise, weigh the tradeoff, give the takeaway, show the proof, and end with one question. Do NOT be terse: expand with concrete details, direct address and specific ifs/thens until you reach the word target. Output only the spoken words per beat: no headings, no stage directions, no commentary.
</task>

<topic>
{json.dumps(payload, ensure_ascii=False)}
</topic>

{grounding}

<voice_rules>
- Open with a concrete consequence for "you": a number, a sound, an image, or a problem. Never open with a topic sentence or a "Why does..." question.
- Use "you" or "your" at least 3 times across the whole script.
- Use contractions wherever natural ("you'll", "it's", "here's", "doesn't"). At least 4 contractions.
- Average sentence 8-12 words. At least three sentences of 6 words or fewer. No sentence over 18 words.
- Put a short fragment in beats 1, 4 and 9 ("Not a bug." "Here's the trick.") with terminal punctuation.
- Add one pattern interrupt by beat 4: a question, an aside, or "Wait—".
- Never start two consecutive sentences with the same word.
- Prefer verbs over nouns; active voice; concrete things (laptop, fan, chef) over abstractions (models, systems, infrastructure).
- End the final beat on a soundbite of 10 words or fewer.
- Exactly 12 beats in this order: hook, stake, context, friction, mechanism_1, mechanism_2, example, aha, tradeoff, payoff, proof, loop.
- Every beat must be DIFFERENT: never repeat a clause, a sentence opening, or the same fact twice.
- Every sentence ends with . ! or ?. Never end on a dangling word like "of", "to", "the", "and", "while", "because", "that", "with".
</voice_rules>

<negative_constraints>
Never use: "In this video", "Today we'll", "Let's dive in", "Imagine", "Picture this", "It's important to note", "However", "Additionally", "Furthermore", "In conclusion", "the fact that", "in order to", "utilize", "facilitate", "implementation", "optimization", "delve", "landscape", "realm", "follow for", "stay curious", "game-changer".
Never write passive voice ("is caused by", "was created by"), noun stacks ("massive AI models", "standard computer processors"), more than one rhetorical question, abstract plural nouns in the first 10 words, or a neutral summary ending.
Do not explain what you are doing.
</negative_constraints>

<few_shot_example>
BAD: "Why do massive AI models stutter when you run them on standard computer processors? You would wait centuries..."
GOOD: "Your laptop can run a giant AI model. It takes centuries. That's not a bug."
</few_shot_example>

Return ONLY a raw JSON object with this exact shape (include ALL 12 beats in the listed order):
{{
  "beats": [
    {{"id": "hook", "focus_word": "...", "lines": ["...", "...", "..."], "narration": "..."}},
    {{"id": "stake", "focus_word": "...", "lines": ["...", "...", "..."], "narration": "..."}},
    ... continue for all 12 ids in order ...
    {{"id": "loop", "focus_word": "...", "lines": ["...", "...", "..."], "narration": "..."}}
  ]
}}"""


def _parse_response(text: str) -> Optional[List[Dict[str, Any]]]:
    text = (text or "").strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", text))
        except json.JSONDecodeError:
            return None
    return data.get("beats") if isinstance(data, dict) else None


def _clean_text(text: str) -> str:
    """Normalize garbled punctuation artifacts from model responses."""
    text = str(text or "")
    text = re.sub(r"[\ufffd\u2014]+\s*\??\s*", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _repair_beats(beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop trailing dangling words so a good script isn't rejected on one token."""
    for beat in beats:
        beat["lines"] = [_clean_text(x) for x in (beat.get("lines") or [])]
        narration = _clean_text(str(beat.get("narration") or ""))
        sentences = [s.strip() for s in _SENT_SPLIT.split(narration) if s.strip()]
        fixed: List[str] = []
        for sentence in sentences:
            parts = sentence.split()
            if len(parts) > 3:
                tail = re.sub(r"[^a-z ]", "", parts[-1].lower()).strip()
                if tail in _DANGLING:
                    parts = parts[:-1]
                    sentence = " ".join(parts).rstrip(".,!?;:") + "."
            fixed.append(sentence)
        beat["narration"] = " ".join(fixed)
    return beats


_BANNED_PHRASES = (
    "in this video", "today we'll", "let's dive in", "imagine", "picture this",
    "it's important to note", "the fact that", "in order to", "utilize",
    "facilitate", "implementation", "optimization", "delve", "landscape",
    "realm", "follow for", "stay curious", "game-changer", "however",
    "additionally", "furthermore", "in conclusion",
)
_PASSIVE_RE = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", re.I)
_CONTRACTION_RE = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.I)
_DANGLING = {
    "of", "to", "the", "a", "an", "and", "but", "while", "because",
    "that", "with", "in", "for", "on", "at", "by", "from", "into",
    "about", "as", "or", "so", "if", "than", "is", "are", "was", "were",
}


def _validate(beats: List[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(beats, list) or len(beats) != SHORT_BEATS:
        return f"expected {SHORT_BEATS} beats"
    if [str(b.get("id") or "") for b in beats] != _BEAT_IDS:
        return "wrong beat ids/order"
    narrations: List[str] = []
    sentences: List[str] = []
    openings: List[str] = []
    seen = set()
    for b in beats:
        narration = re.sub(r"\s+", " ", str(b.get("narration") or "").strip())
        if is_slop(narration):
            return f"beat {b.get('id')} has slop"
        beat_sentences = [s.strip() for s in _SENT_SPLIT.split(narration) if s.strip()]
        if not beat_sentences:
            return f"beat {b.get('id')} has no sentences"
        for sentence in beat_sentences:
            n = len(sentence.split())
            if n > 18:
                return f"beat {b.get('id')} has a sentence over 18 words"
            if sentence[-1] not in ".!?":
                return f"beat {b.get('id')} has an unterminated sentence"
            sentences.append(sentence)
            openings.append(sentence.split()[0].lower())
        key = re.sub(r"\W+", " ", narration.lower()).strip()
        if key in seen:
            return "duplicate beat narration"
        seen.add(key)
        narrations.append(narration)

    total = sum(len(n.split()) for n in narrations)
    if not (SHORT_WORD_MIN <= total <= SHORT_WORD_MAX):
        return f"total word count {total}"
    mean_sentence = total / max(1, len(sentences))
    if mean_sentence > 16:
        return f"mean sentence length too high ({mean_sentence:.1f})"
    fragments = sum(1 for s in sentences if len(s.split()) <= 6)
    if fragments < 2:
        return f"too few spoken fragments ({fragments})"

    all_text = " ".join(narrations)
    lowered = all_text.lower()
    if len(re.findall(r"\b(?:you|your)\b", lowered)) < 2:
        return "not enough second-person framing"
    if len(_CONTRACTION_RE.findall(all_text)) < 2:
        return "not enough contractions"
    for phrase in _BANNED_PHRASES:
        if phrase in lowered:
            return f"banned article-style phrase: {phrase}"
    if all_text.count("?") > 3:
        return "too many rhetorical questions"
    if any(openings[i] == openings[i + 1] for i in range(len(openings) - 1)):
        return "two consecutive sentences share an opening word"
    if len(sentences[-1].split()) > 10:
        return "final soundbite is too long"
    return None


def build_short_script_ai(topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a validated AI script payload, or None to use the fallback."""
    try:
        import config
        from google import genai

        api_key = getattr(config, "GEMINI_API_KEY", "")
        if not api_key:
            return None
        client = genai.Client(
            api_key=api_key,
            http_options=genai.types.HttpOptions(
                timeout=30000,
                retry_options=genai.types.HttpRetryOptions(attempts=1),
            ),
        )
        models = [getattr(config, "GEMINI_MODEL", "gemini-3.5-flash"),
                  "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
        models = list(dict.fromkeys([m for m in models if m]))
        prompt = _prompt(topic)
    except Exception as exc:
        print(f"[ShortScriptAI] setup failed: {exc}")
        return None

    for model in models:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            beats_raw = _parse_response(getattr(response, "text", ""))
            if beats_raw:
                beats_raw = _repair_beats(beats_raw)
            error = _validate(beats_raw or [])
            if error:
                print(f"[ShortScriptAI] {model} rejected: {error}")
                continue
            beats = []
            for b in beats_raw:
                bid = str(b["id"])
                narration = re.sub(r"\s+", " ", str(b["narration"]).strip())
                lines = [str(x).strip() for x in (b.get("lines") or []) if str(x).strip()][:3]
                beats.append({
                    "id": bid,
                    "label": _LABELS[bid],
                    "focus_word": str(b.get("focus_word") or bid)[:40],
                    "lines": lines,
                    "narration": narration,
                    "target_s": _TARGET_S[bid],
                })
            narration = " ".join(b["narration"] for b in beats)
            words = narration.split()
            qa = {
                "word_count": len(words),
                "estimated_seconds_at_145wpm": round(len(words) / SHORT_WPM * 60, 1),
                "flags": [],
                "source": f"gemini:{model}",
            }
            print(f"[ShortScriptAI] wrote a fresh script with {model} ({len(words)} words)")
            return {
                "title": str(topic.get("title") or "AI Explained"),
                "beats": beats,
                "narration": narration,
                "words": words,
                "qa": qa,
            }
        except Exception as exc:
            print(f"[ShortScriptAI] {model} failed: {exc}")
            continue
    return None
