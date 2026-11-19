"""Gemini-powered structured visual storyboard for 45s tech Shorts.

The renderer owns a closed vocabulary of animation recipes (templates). This
module does NOT let the model invent arbitrary visuals: it asks Gemini to pick,
for each of the 7 script beats, one recipe from that vocabulary plus short
labels and recipe params. The output is validated strictly and ``None`` is
returned on failure so callers can fall back to
:func:`deterministic_storyboard`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# The closed animation-recipe vocabulary owned by our renderer.
ALLOWED_TEMPLATES = (
    "flood",
    "queue",
    "parallel_grid",
    "race",
    "bottleneck",
    "merge",
    "payoff",
)
ALLOWED_CAMERAS = ("dolly_in", "zoom_out", "pan_right", "none")

# Topics marked as NEWS lean on these recipes; everything else on the rest.
NEWS_TEMPLATES = ("flood", "queue", "race", "bottleneck")
CONCEPT_TEMPLATES = ("parallel_grid", "merge", "payoff")

# Fallback palette keys, reused by both the AI normalizer and the deterministic
# builder.
_PALETTE_KEYS = ("primary", "secondary", "accent", "bg")
_FALLBACK_PALETTES = {
    "news": {
        "primary": "#fbbf24",
        "secondary": "#f43f5e",
        "accent": "#fde68a",
        "bg": "#0b0f1a",
    },
    "concept": {
        "primary": "#22d3ee",
        "secondary": "#34d399",
        "accent": "#a5f3fc",
        "bg": "#06080d",
    },
}

# Disallowed "scaffolding" labels that must never appear on screen.
_SCAFFOLDING = {
    "the hook", "why it matters", "the setup", "how it works",
    "the surprise", "your move", "the loop", "hook", "stake",
    "context", "mechanism", "aha", "payoff", "loop",
}

_HEX_RE = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# ---------------------------------------------------------------------------
# Prompt / parsing helpers
# ---------------------------------------------------------------------------
def _is_news(topic: dict, script: dict) -> bool:
    """Return True when the topic pillar/title indicates a news item."""
    blob = " ".join([
        str(topic.get("pillar") or ""),
        str(topic.get("category") or ""),
        str(topic.get("title") or ""),
        str(script.get("title") or ""),
    ]).lower()
    return any(word in blob for word in ("news", "breaking", "headline"))


def _prompt(topic: dict, script: dict) -> str:
    """Build the visual-director prompt from the topic and validated script."""
    topic_payload = {
        "title": str(topic.get("title") or ""),
        "summary": str(topic.get("summary") or ""),
        "hook": str(topic.get("hook") or ""),
        "pillar": str(topic.get("pillar") or ""),
        "entities": topic.get("entities") or [],
    }
    beats_payload: List[Dict[str, Any]] = []
    for beat in script.get("beats") or []:
        if not isinstance(beat, dict):
            continue
        beats_payload.append({
            "id": str(beat.get("id") or ""),
            "label": str(beat.get("label") or ""),
            "focus_word": str(beat.get("focus_word") or ""),
            "lines": [str(x) for x in (beat.get("lines") or [])][:2],
            "narration": str(beat.get("narration") or "")[:240],
            "target_s": beat.get("target_s"),
        })

    news = _is_news(topic, script)
    lean = (
        "This is a NEWS topic: prefer the flood, queue, race and bottleneck "
        "recipes to visualise events, volume, urgency and constraints."
        if news else
        "This is a CONCEPT/EXPLAINER topic: prefer the parallel_grid, merge "
        "and payoff recipes to visualise structure, combination and result."
    )

    return f"""You are a visual director for a 45-second, silent-understandable tech Short.
The viewer watches with sound OFF, so the picture plus on-screen text must carry the whole idea.

TOPIC:
{json.dumps(topic_payload, ensure_ascii=False)}

SCRIPT BEATS (7, in order) — these are facts and narration you must NOT copy verbatim:
{json.dumps(beats_payload, ensure_ascii=False)}

{lean}

Choose one animation RECIPE per beat from this CLOSED vocabulary (never invent a new one):
- flood: many items pour into a scene (volume / impact).
- queue: items line up and wait in order (backlog / latency).
- parallel_grid: cells work side by side at once (concurrency / batching).
- race: lanes compete to a finish line (speed / comparison).
- bottleneck: flow squeezes through a narrow gap (constraint / failure).
- merge: separate streams combine into one (integration / synthesis).
- payoff: a single result or number lands large (outcome / takeaway).

For EACH of the 7 beats output a JSON object with EXACTLY these six keys:
- "template_id": one of flood, queue, parallel_grid, race, bottleneck, merge, payoff.
- "on_screen_text": max 5 words, a short label or number only, NEVER a sentence.
- "focus_label": 1-3 words of optional accent label (may be empty).
- "params": an object of numeric/string params appropriate to that recipe
  (e.g. counts, values, labels, number strings such as {{"count": 12, "label": "requests"}}).
- "camera": one of dolly_in, zoom_out, pan_right, none.
- "visual_metaphor": a short phrase describing the image for internal review only.

Also output a top-level "palette" object with keys "primary", "secondary", "accent", "bg",
each a hex color like "#22d3ee".

HARD RULES:
- Use at least 4 DIFFERENT template_ids across the 7 beats.
- on_screen_text is <= 5 words and is a label/number, never a sentence.
- Do NOT repeat any sentence from a beat's narration on screen.
- NEVER use scaffolding labels such as "The Hook" or "Why It Matters" as on-screen text.
- Match the recipe to the beat's role, but keep every recipe from the closed vocabulary.

Return ONLY a raw JSON object with this exact shape:
{{
  "beats": [
    {{"template_id": "...", "on_screen_text": "...", "focus_label": "...", "params": {{}}, "camera": "...", "visual_metaphor": "..."}},
    ... seven objects total, in the same order as the script beats ...
  ],
  "palette": {{"primary": "#...", "secondary": "#...", "accent": "#...", "bg": "#..."}}
}}"""


def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    """Extract the JSON object from a model reply, tolerating code fences."""
    text = (text or "").strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", text))
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Validation / normalization helpers
# ---------------------------------------------------------------------------
def _words(value: Any) -> List[str]:
    """Split a value into lowercase, punctuation-stripped word tokens."""
    return re.sub(r"[^\w\s]", " ", str(value or "")).lower().split()


def _normalize_hex(value: Any) -> Optional[str]:
    """Return a '#' hex color when valid, else None."""
    text = str(value or "").strip()
    if not _HEX_RE.match(text):
        return None
    return text if text.startswith("#") else "#" + text


def _narration_sentences(script: dict) -> set:
    """Set of normalized narration sentences that must not be shown on screen."""
    out = set()
    narrations: List[str] = []
    if str(script.get("narration") or "").strip():
        narrations.append(str(script["narration"]))
    for beat in script.get("beats") or []:
        if isinstance(beat, dict) and str(beat.get("narration") or "").strip():
            narrations.append(str(beat["narration"]))
    for narration in narrations:
        for sentence in re.split(r"(?<=[.!?])\s+", narration):
            tokens = _words(sentence)
            if tokens:
                out.add(" ".join(tokens))
    return out


def _validate(data: Dict[str, Any], script: dict) -> Optional[str]:
    """Return a rejection reason, or None when the payload is acceptable."""
    beats = data.get("beats")
    if not isinstance(beats, list) or len(beats) != 7:
        return "expected 7 beats"

    palette = data.get("palette")
    if not isinstance(palette, dict):
        return "missing palette"
    for key in _PALETTE_KEYS:
        if _normalize_hex(palette.get(key)) is None:
            return f"bad palette color: {key}"

    sentences = _narration_sentences(script)
    forbidden = set(_SCAFFOLDING)
    for beat in script.get("beats") or []:
        if isinstance(beat, dict):
            label = str(beat.get("label") or "").strip().lower()
            if label:
                forbidden.add(label)

    templates: List[str] = []
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            return f"beat {index} not an object"
        template = str(beat.get("template_id") or "").strip()
        if template not in ALLOWED_TEMPLATES:
            return f"beat {index} bad template_id: {template}"
        camera = str(beat.get("camera") or "").strip()
        if camera not in ALLOWED_CAMERAS:
            return f"beat {index} bad camera: {camera}"
        text = str(beat.get("on_screen_text") or "").strip()
        text_words = _words(text)
        if not text_words or len(text_words) > 5:
            return f"beat {index} on_screen_text word count {len(text_words)}"
        focus = str(beat.get("focus_label") or "").strip()
        focus_words = _words(focus)
        if len(focus_words) > 3:
            return f"beat {index} focus_label word count {len(focus_words)}"
        if " ".join(text_words) in forbidden or " ".join(focus_words) in forbidden:
            return f"beat {index} uses scaffolding label"
        if " ".join(text_words) in sentences:
            return f"beat {index} on_screen_text copies narration"
        if not isinstance(beat.get("params"), dict):
            return f"beat {index} params not an object"
        templates.append(template)

    if len(set(templates)) < 4:
        return f"only {len(set(templates))} distinct templates (need 4)"
    return None


def _normalize(data: Dict[str, Any], model: str) -> Dict[str, Any]:
    """Coerce a validated payload into the exact public beat-key shape."""
    beats: List[Dict[str, Any]] = []
    for raw in data["beats"]:
        text = " ".join(str(raw.get("on_screen_text") or "").split())[:60]
        beats.append({
            "template_id": str(raw["template_id"]),
            "on_screen_text": text,
            "focus_label": " ".join(str(raw.get("focus_label") or "").split())[:40],
            "params": dict(raw.get("params") or {}),
            "camera": str(raw["camera"]),
            "visual_metaphor": str(raw.get("visual_metaphor") or "").strip()[:120],
        })
    palette = {key: _normalize_hex(data["palette"].get(key)) for key in _PALETTE_KEYS}
    return {
        "beats": beats,
        "palette": palette,
        "source": f"gemini:{model}",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_storyboard_ai(topic: dict, script: dict) -> Optional[dict]:
    """Return a validated, Gemini-generated structured storyboard, or ``None``.

    On ``None`` the caller should use :func:`deterministic_storyboard`.
    """
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
        models = [
            getattr(config, "GEMINI_MODEL", "gemini-3.5-flash"),
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ]
        models = list(dict.fromkeys([m for m in models if m]))
        prompt = _prompt(topic or {}, script or {})
    except Exception as exc:
        print(f"[StoryboardAI] setup failed: {exc}")
        return None

    for model in models:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            data = _parse_response(getattr(response, "text", ""))
            error = _validate(data or {}, script or {})
            if error:
                print(f"[StoryboardAI] {model} rejected: {error}")
                continue
            result = _normalize(data, model)
            print(f"[StoryboardAI] built a 7-beat storyboard with {model}")
            return result
        except Exception as exc:
            print(f"[StoryboardAI] {model} failed: {exc}")
            continue
    return None


def deterministic_storyboard(topic: dict, script: dict) -> dict:
    """Return a fixed, renderer-safe storyboard used when Gemini is unavailable.

    Templates follow the fixed sequence flood, queue, parallel_grid, race,
    bottleneck, merge, payoff with generic params and a pillar-based palette.
    """
    script = script or {}
    topic = topic or {}

    sequence = [
        ("flood", {"count": 40, "label": "requests"}, "dolly_in", "a surge of items pouring in", "SURGE"),
        ("queue", {"count": 12, "label": "items"}, "pan_right", "items waiting in a line", "WAITING"),
        ("parallel_grid", {"rows": 3, "cols": 4, "label": "workers"}, "zoom_out", "cells working side by side", "PARALLEL"),
        ("race", {"lanes": 3, "labels": ["A", "B", "C"], "winner": "A"}, "dolly_in", "lanes racing to the finish", "SPEED"),
        ("bottleneck", {"capacity": 5, "label": "pipeline", "pressure": 3}, "zoom_out", "flow squeezing through a gap", "LIMIT"),
        ("merge", {"inputs": 3, "label": "streams"}, "pan_right", "streams combining into one", "COMBINE"),
        ("payoff", {"value": "10x", "label": "gain"}, "dolly_in", "one result landing large", "RESULT"),
    ]

    script_beats = [b for b in (script.get("beats") or []) if isinstance(b, dict)]
    beats: List[Dict[str, Any]] = []
    for index, (template, params, camera, metaphor, focus) in enumerate(sequence):
        source = script_beats[index] if index < len(script_beats) else {}
        text = " ".join(str(source.get("focus_word") or "idea").split())[:60] or "idea"
        text_words = _words(text)
        if not text_words or len(text_words) > 5:
            text = " ".join(text_words[:5]) or "idea"
        beats.append({
            "template_id": template,
            "on_screen_text": text,
            "focus_label": focus,
            "params": dict(params),
            "camera": camera,
            "visual_metaphor": metaphor,
        })

    palette_key = "news" if _is_news(topic, script) else "concept"
    result = {
        "beats": beats,
        "palette": dict(_FALLBACK_PALETTES[palette_key]),
        "source": "deterministic",
    }
    print("[StoryboardAI] using deterministic storyboard fallback")
    return result
