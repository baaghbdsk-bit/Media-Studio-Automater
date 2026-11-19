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

_BEAT_IDS = ["hook", "stake", "context", "mechanism", "aha", "payoff", "loop"]
_LABELS = {
    "hook": "The Hook",
    "stake": "Why It Matters",
    "context": "The Setup",
    "mechanism": "How It Works",
    "aha": "The Surprise",
    "payoff": "Your Move",
    "loop": "The Loop",
}
_TARGET_S = {
    "hook": 2.5, "stake": 5.0, "context": 7.0, "mechanism": 11.0,
    "aha": 8.0, "payoff": 9.0, "loop": 5.0,
}
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
        "numbers, or outcome." if news else
        "Use the topic fields as factual anchors. Explain one mechanism clearly."
    )
    return f"""You are a senior short-form video script editor. Write ONE 45-55 second YouTube Short script.

TOPIC:
{json.dumps(payload, ensure_ascii=False)}

{grounding}

HARD RULES:
- Exactly 7 beats in this order: hook, stake, context, mechanism, aha, payoff, loop.
- Total spoken words: 100-120. Each beat narration: 12-22 words.
- One idea only: a question, one mechanism, one surprising implication.
- Sentences <= 20 words. Use contractions and second person. Write for the ear.
- Each beat must be DIFFERENT: never repeat a clause, a sentence opening, or the same fact twice.
- Every beat narration must be a COMPLETE sentence with a finished object. Never end on "of", "to", "the", "and", "while", "because", "that", "with", "in", "for", "on", or any other dangling word.
- No "follow for", "stay curious", "game-changer", "delve", "in today's fast-paced", "here is what we know so far".
- No greetings, no logo intro, no "in this video". Hook starts mid-thought with a specific question or consequence.
- The final beat is a short callback to the opening question so the video loops cleanly.
- focus_word: 1-3 words that anchor that beat on screen.
- lines: one or two very short on-screen lines (max 6 words each), not a copy of the narration.

Return ONLY a raw JSON object with this exact shape:
{{
  "beats": [
    {{"id": "hook", "focus_word": "...", "lines": ["..."], "narration": "..."}},
    {{"id": "stake", "focus_word": "...", "lines": ["..."], "narration": "..."}},
    {{"id": "context", "focus_word": "...", "lines": ["..."], "narration": "..."}},
    {{"id": "mechanism", "focus_word": "...", "lines": ["..."], "narration": "..."}},
    {{"id": "aha", "focus_word": "...", "lines": ["..."], "narration": "..."}},
    {{"id": "payoff", "focus_word": "...", "lines": ["..."], "narration": "..."}},
    {{"id": "loop", "focus_word": "...", "lines": ["..."], "narration": "..."}}
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


def _validate(beats: List[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(beats, list) or len(beats) != 7:
        return "expected 7 beats"
    if [str(b.get("id") or "") for b in beats] != _BEAT_IDS:
        return "wrong beat ids/order"
    narrations = []
    seen = set()
    for b in beats:
        narration = re.sub(r"\s+", " ", str(b.get("narration") or "").strip())
        words = narration.split()
        if len(words) < 10 or len(words) > 26:
            return f"beat {b.get('id')} word count {len(words)}"
        if is_slop(narration):
            return f"beat {b.get('id')} has slop"
        for sentence in _SENT_SPLIT.split(narration):
            if len(sentence.split()) > 20:
                return f"beat {b.get('id')} has a sentence over 20 words"
            if sentence.rstrip() and sentence.rstrip()[-1] not in ".!?":
                return f"beat {b.get('id')} has an unterminated sentence"
            tail = re.sub(r"[^a-z ]", "", sentence.lower()).split()[-1:]
            if tail and tail[0] in {
                "of", "to", "the", "a", "an", "and", "but", "while", "because",
                "that", "with", "in", "for", "on", "at", "by", "from", "into",
                "about", "as", "or", "so", "if", "than", "is", "are", "was", "were",
            }:
                return f"beat {b.get('id')} ends on a dangling word: {tail[0]}"
        key = re.sub(r"\W+", " ", narration.lower()).strip()
        if key in seen:
            return "duplicate beat narration"
        seen.add(key)
        narrations.append(narration)
    total = sum(len(n.split()) for n in narrations)
    if not (95 <= total <= 125):
        return f"total word count {total}"
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
            error = _validate(beats_raw or [])
            if error:
                print(f"[ShortScriptAI] {model} rejected: {error}")
                continue
            beats = []
            for b in beats_raw:
                bid = str(b["id"])
                narration = re.sub(r"\s+", " ", str(b["narration"]).strip())
                lines = [str(x).strip() for x in (b.get("lines") or []) if str(x).strip()][:2]
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
                "estimated_seconds_at_145wpm": round(len(words) / 145 * 60, 1),
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
