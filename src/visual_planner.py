"""Semantic visual planning for 45-second tech Shorts.

This module converts the seven narration beats produced by
``src.short_script_ai.build_short_script_ai`` into a strict *semantic* scene
specification.  Scene identity is derived from what each beat is actually
about (products, companies, people, objects, software, concepts, statistics)
rather than from a fixed seven-template animation vocabulary.

Two entry points are provided:

* :func:`build_visual_plan` -- the primary path, using Gemini, which returns a
  fully validated plan or ``None`` so callers can fall back safely.
* :func:`deterministic_visual_plan` -- an offline, dependency-free safety net
  with the same output schema.

The public schema is documented in :func:`_validate`; every plan returned by
either entry point is guaranteed to satisfy it.
"""

from __future__ import annotations

import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Closed vocabularies used by the schema and by validation.
# ---------------------------------------------------------------------------
ENTITY_TYPES = (
    "product", "company", "person", "physical_object", "software",
    "concept", "metric", "none",
)
VISUAL_TYPES = (
    "stock_image", "stock_footage", "illustration", "diagram", "chart",
    "ui_mock", "official_media",
)
MODALITIES = ("image", "video", "svg", "markup")
CAMERAS = ("dolly_in", "zoom_out", "pan_right", "static_push")
ANIMATIONS = (
    "slow_push", "flow_packet", "count_up", "reveal_layers", "morph",
    "parallax", "none",
)
TRANSITIONS = ("wipe", "zoom", "morph", "cut")
FALLBACKS = ("illustration", "diagram", "ui_mock", "none")

REQUIRED_SCENE_KEYS = (
    "scene_id", "narration_span", "main_visual_concept", "entities",
    "visual_type", "asset_requirements", "search_keywords", "camera",
    "animation", "transition", "duration_s", "fallback_strategy",
    "relevance_assessed",
)

# ---------------------------------------------------------------------------
# Deterministic keyword intelligence.
# ---------------------------------------------------------------------------
# Lowercase keyword -> (canonical entity name, entity type).  Multi-word
# phrases are matched before single words.
_KEYWORD_ENTITIES: dict[str, tuple[str, str]] = {
    "data center": ("data center", "physical_object"),
    "datacenter": ("data center", "physical_object"),
    "graphics card": ("graphics card", "product"),
    "neural network": ("neural network", "software"),
    "search engine": ("search engine", "software"),
    "social media": ("social media", "software"),
    "gpu": ("GPU", "product"),
    "cpu": ("CPU", "product"),
    "chip": ("chip", "product"),
    "processor": ("processor", "product"),
    "laptop": ("laptop", "product"),
    "smartphone": ("smartphone", "product"),
    "phone": ("phone", "product"),
    "server": ("server", "product"),
    "device": ("device", "product"),
    "robot": ("robot", "physical_object"),
    "factory": ("factory", "physical_object"),
    "warehouse": ("warehouse", "physical_object"),
    "agent": ("AI agent", "software"),
    "agents": ("AI agent", "software"),
    "agentic": ("AI agent", "software"),
    "model": ("AI model", "software"),
    "models": ("AI model", "software"),
    "llm": ("LLM", "software"),
    "api": ("API", "software"),
    "app": ("app", "software"),
    "software": ("software", "software"),
    "database": ("database", "software"),
    "workflow": ("workflow", "software"),
    "benchmark": ("benchmark", "metric"),
    "benchmarks": ("benchmark", "metric"),
    "statistics": ("statistics", "metric"),
    "percentage": ("percentage", "metric"),
    "percent": ("percentage", "metric"),
    "speedup": ("speedup", "metric"),
    "latency": ("latency", "metric"),
    "pipeline": ("pipeline", "concept"),
    "news": ("news report", "concept"),
    "chart": ("chart", "concept"),
    "graph": ("graph", "concept"),
    "bottleneck": ("bottleneck", "concept"),
}

_KNOWN_COMPANIES = (
    "nvidia", "openai", "google", "deepmind", "meta", "microsoft", "apple",
    "amazon", "tesla", "anthropic", "qualcomm", "amd", "intel", "samsung",
    "tsmc", "oracle", "ibm", "cohere", "mistral", "hugging face",
    "huggingface", "github", "netflix", "spotify",
)

# Capitalized words that are ordinary sentence openers, not named entities.
_CAPS_STOPLIST = {
    "the", "a", "an", "this", "that", "these", "those", "your", "you", "its",
    "it", "each", "every", "now", "inside", "think", "here", "when", "while",
    "before", "after", "then", "because", "wait", "not", "one", "two", "three",
    "and", "but", "so", "if", "with", "without", "what", "why", "how", "who",
    "imagine", "picture", "first", "second", "third", "next", "last", "look",
    "watch", "see", "by", "in", "on", "at", "as", "for", "from", "into", "up",
    "down", "out", "over", "under", "most", "more", "less", "some", "all",
    "which", "both", "pick", "stop", "start", "across", "even", "still",
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are",
    "was", "were", "on", "with", "your", "you", "it", "its", "that", "this",
    "how", "why", "from", "as", "at", "by", "be", "into", "not", "but",
    "will", "can", "just", "one", "two", "get", "got", "does", "did", "has",
    "have", "had", "they", "them", "their", "then", "than", "when", "where",
    "what", "who", "which", "about", "out", "up", "down", "over", "under",
    "very", "really", "much", "many", "some", "all", "more", "most", "less",
}

_STYLE_HINTS = {
    "stock_image": "photograph",
    "stock_footage": "footage",
    "illustration": "illustration",
    "diagram": "explainer diagram",
    "chart": "data chart",
    "ui_mock": "software interface screenshot",
    "official_media": "official press photo",
}
_CAMERA_BY_TYPE = {
    "stock_image": "dolly_in",
    "stock_footage": "dolly_in",
    "illustration": "static_push",
    "diagram": "pan_right",
    "chart": "static_push",
    "ui_mock": "zoom_out",
    "official_media": "static_push",
}
_ANIMATION_BY_TYPE = {
    "stock_image": "parallax",
    "stock_footage": "slow_push",
    "illustration": "morph",
    "diagram": "reveal_layers",
    "chart": "count_up",
    "ui_mock": "flow_packet",
    "official_media": "slow_push",
}
_FALLBACK_BY_TYPE = {
    "stock_image": "illustration",
    "stock_footage": "illustration",
    "illustration": "illustration",
    "diagram": "diagram",
    "chart": "diagram",
    "ui_mock": "ui_mock",
    "official_media": "illustration",
}
_TRANSITION_CYCLE = ("cut", "wipe", "zoom", "morph", "cut", "wipe", "zoom")


# ---------------------------------------------------------------------------
# Small text helpers shared by both planning paths.
# ---------------------------------------------------------------------------
def _clean(value: Any) -> str:
    """Return a whitespace-normalized string (never ``None``)."""
    return " ".join(str(value or "").split()).strip()


def _tokens(value: Any) -> list[str]:
    """Strip punctuation and split into lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(value or "").lower())


def _as_float(value: Any, default: float = 0.0) -> float:
    """Best-effort float conversion with a finite fallback."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if result == result and result not in (float("inf"), float("-inf")) else default


def _clamp_duration(value: float) -> float:
    """Clamp a duration into the schema's legal 0.5-15 second window."""
    return round(min(15.0, max(0.5, value)), 3)


# ---------------------------------------------------------------------------
# Strict schema validation.
# ---------------------------------------------------------------------------
def _validate(plan: Any) -> str | None:
    """Return a rejection reason for an invalid plan, else ``None``.

    The check is intentionally strict: exactly seven scenes with sequential
    ids, all required keys with the correct types, closed enums for every
    categorical field, a 0.5-15s duration, non-empty narration text, 2-6
    search keywords, ``relevance_assessed is True``, and no repeated
    ``main_visual_concept``.  AI candidates that fail here are retried with
    the next model.
    """
    if not isinstance(plan, dict):
        return "plan is not an object"
    if not isinstance(plan.get("topic"), str) or not plan["topic"].strip():
        return "topic must be a non-empty string"
    source = plan.get("source")
    if not isinstance(source, str) or not (
        source == "deterministic"
        or (source.startswith("gemini:") and len(source) > len("gemini:"))
    ):
        return "bad source"
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 7:
        return "expected exactly 7 scenes"

    concepts: set[str] = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            return f"scene {index} is not an object"
        missing = [key for key in REQUIRED_SCENE_KEYS if key not in scene]
        if missing:
            return f"scene {index} missing keys: {missing}"

        scene_id = scene["scene_id"]
        if isinstance(scene_id, bool) or not isinstance(scene_id, int) or scene_id != index + 1:
            return f"scene {index} has non-sequential scene_id"

        span = scene["narration_span"]
        if not isinstance(span, dict):
            return f"scene {index} narration_span is not an object"
        start, end = span.get("start_s"), span.get("end_s")
        if isinstance(start, bool) or not isinstance(start, (int, float)) or start < 0:
            return f"scene {index} bad narration start_s"
        if isinstance(end, bool) or not isinstance(end, (int, float)) or end < start:
            return f"scene {index} bad narration end_s"
        if not isinstance(span.get("text"), str) or not span["text"].strip():
            return f"scene {index} empty narration text"

        concept = scene["main_visual_concept"]
        if not isinstance(concept, str) or not concept.strip():
            return f"scene {index} empty main_visual_concept"
        concept_key = re.sub(r"\W+", " ", concept.lower()).strip()
        if concept_key in concepts:
            return f"scene {index} duplicate main_visual_concept"
        concepts.add(concept_key)

        entities = scene["entities"]
        if not isinstance(entities, list):
            return f"scene {index} entities is not a list"
        for entity in entities:
            if not isinstance(entity, dict):
                return f"scene {index} entity is not an object"
            if not isinstance(entity.get("name"), str) or not entity["name"].strip():
                return f"scene {index} bad entity name"
            if entity.get("type") not in ENTITY_TYPES:
                return f"scene {index} bad entity type: {entity.get('type')}"
            confidence = entity.get("confidence")
            if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                    or not 0.0 <= float(confidence) <= 1.0):
                return f"scene {index} bad entity confidence"

        if scene["visual_type"] not in VISUAL_TYPES:
            return f"scene {index} bad visual_type: {scene['visual_type']}"

        asset = scene["asset_requirements"]
        if not isinstance(asset, dict):
            return f"scene {index} asset_requirements is not an object"
        if asset.get("modality") not in MODALITIES:
            return f"scene {index} bad modality: {asset.get('modality')}"
        if not isinstance(asset.get("query"), str) or not asset["query"].strip():
            return f"scene {index} bad asset query"
        min_size = asset.get("min_size")
        if (not isinstance(min_size, (list, tuple)) or len(min_size) != 2
                or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in min_size)):
            return f"scene {index} bad min_size"
        avoid = asset.get("avoid")
        if not isinstance(avoid, list) or any(not isinstance(item, str) for item in avoid):
            return f"scene {index} bad avoid list"

        keywords = scene["search_keywords"]
        if (not isinstance(keywords, list) or not 2 <= len(keywords) <= 6
                or any(not isinstance(word, str) or not word.strip() for word in keywords)):
            return f"scene {index} bad search_keywords"

        if scene["camera"] not in CAMERAS:
            return f"scene {index} bad camera: {scene['camera']}"
        if scene["animation"] not in ANIMATIONS:
            return f"scene {index} bad animation: {scene['animation']}"
        if scene["transition"] not in TRANSITIONS:
            return f"scene {index} bad transition: {scene['transition']}"

        duration = scene["duration_s"]
        if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                or not 0.5 <= float(duration) <= 15.0):
            return f"scene {index} bad duration_s: {duration}"
        if scene["fallback_strategy"] not in FALLBACKS:
            return f"scene {index} bad fallback_strategy: {scene['fallback_strategy']}"
        if scene["relevance_assessed"] is not True:
            return f"scene {index} relevance_assessed is not true"
    return None


# ---------------------------------------------------------------------------
# Narration timing.
# ---------------------------------------------------------------------------
def _normalized_beats(script: dict, topic: dict) -> list[dict[str, Any]]:
    """Return exactly seven normalized beat dicts (padding if necessary)."""
    beats: list[dict[str, Any]] = []
    for raw in (script.get("beats") or []):
        if not isinstance(raw, dict):
            continue
        lines = [str(x).strip() for x in (raw.get("lines") or []) if str(x).strip()]
        narration = _clean(raw.get("narration")) or " ".join(lines)
        beats.append({
            "narration": narration or f"Beat {len(beats) + 1} detail.",
            "focus_word": _clean(raw.get("focus_word")),
            "label": _clean(raw.get("label")),
            "target_s": _as_float(raw.get("target_s"), 5.0),
        })
        if len(beats) == 7:
            break
    title = _clean(topic.get("title")) or _clean(script.get("title")) or "This topic"
    while len(beats) < 7:
        beats.append({
            "narration": f"{title} has one more concrete detail to show.",
            "focus_word": "",
            "label": "",
            "target_s": 5.0,
        })
    return beats[:7]


def _narration_spans(beats: list[dict[str, Any]], words: list[dict]) -> list[dict[str, Any]]:
    """Map every beat onto a word-timed narration span.

    Beat narration tokens are matched sequentially against the chronological
    word-timing list from ``voice.synthesize_performance``.  If *every* beat
    can be matched, those exact word boundaries are used; otherwise the spans
    fall back to a proportional split of ``target_s`` across the narration
    duration.  Both branches are monotonic, so spans never overlap or reverse.
    """
    flat: list[tuple[str, int]] = []
    for index, word in enumerate(words):
        if not isinstance(word, dict):
            continue
        for token in _tokens(word.get("text")):
            flat.append((token, index))

    matched: list[tuple[int, int] | None] = []
    pointer = 0
    for beat in beats:
        indices: list[int] = []
        for token in _tokens(beat["narration"]):
            cursor = pointer
            while cursor < len(flat) and flat[cursor][0] != token:
                cursor += 1
            if cursor < len(flat):
                indices.append(flat[cursor][1])
                pointer = cursor + 1
        if indices:
            matched.append((indices[0], indices[-1]))
        else:
            matched.append(None)

    spans: list[dict[str, Any]] = []
    if flat and all(pair is not None for pair in matched):
        for beat, pair in zip(beats, matched):
            first, last = pair  # type: ignore[misc]
            start = round(_as_float(words[first].get("start")), 3)
            end = round(_as_float(words[last].get("end")), 3)
            if end <= start:
                end = start + 0.5
            spans.append({"start_s": start, "end_s": end, "text": _clean(beat["narration"])})
        return spans

    # Proportional fallback driven by the beat target durations.
    targets = [max(0.1, beat["target_s"]) for beat in beats]
    total_target = sum(targets)
    audio_end = max((_as_float(w.get("end")) for w in words if isinstance(w, dict)), default=0.0)
    total = audio_end if audio_end > 0 else total_target
    if total <= 0:
        total = float(len(beats))
        targets = [1.0] * len(beats)
    scale = total / sum(targets)
    cursor = 0.0
    for beat, target in zip(beats, targets):
        start = round(cursor * scale, 3)
        cursor += target
        end = round(cursor * scale, 3)
        if end <= start:
            end = start + 0.5
        spans.append({"start_s": start, "end_s": end, "text": _clean(beat["narration"])})
    return spans


# ---------------------------------------------------------------------------
# Deterministic semantic reasoning.
# ---------------------------------------------------------------------------
def _extract_entities(text: str, seed: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Derive candidate entities from text using keywords and capitalized names."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name: str, entity_type: str, confidence: float) -> None:
        key = name.lower()
        for existing in out:
            if existing["name"].lower() == key:
                existing["confidence"] = round(max(existing["confidence"], confidence), 3)
                return
        if key in seen:
            return
        seen.add(key)
        out.append({"name": name, "type": entity_type, "confidence": round(confidence, 3)})

    # Text-local subjects come first so they dominate the scene concept.
    lowered = str(text or "").lower()
    tokens = set(_tokens(text))
    for phrase in sorted(_KEYWORD_ENTITIES, key=lambda item: (-len(item), item)):
        if re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
            name, entity_type = _KEYWORD_ENTITIES[phrase]
            add(name, entity_type, 0.95 if " " in phrase or len(phrase) > 3 else 0.85)
    for company in _KNOWN_COMPANIES:
        if re.search(r"\b" + re.escape(company) + r"\b", lowered):
            add(company.title(), "company", 0.9)
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9]+\b", str(text or "")):
        name = match.group(0)
        if name.lower() not in _CAPS_STOPLIST and name.lower() not in seen:
            add(name, "company", 0.7)

    # Topic-level entities enrich but never outrank the beat's own subjects.
    for entity in (seed or []):
        add(entity["name"], entity["type"], min(0.65, entity["confidence"]))

    if not out:
        return [{"name": "none", "type": "none", "confidence": 1.0}]
    return out[:4]


def _classify_visual_type(text: str, entities: list[dict[str, Any]]) -> str:
    """Choose the visual_type best depicting the subject of one beat."""
    lowered = str(text or "").lower()
    number_re = (
        r"\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\s*[xX]\b|[$€£]\s*\d|"
        r"\b\d+(?:\.\d+)?\s*(?:million|billion|thousand|seconds?|minutes?|"
        r"hours?|frames?|tokens?|watts?|cores?|percent)\b"
    )
    if re.search(number_re, lowered):
        return "chart"
    if any(word in lowered for word in (
        "workflow", "pipeline", "flow", "steps", "how it works", "mechanism",
        "process", "architecture", "connect", "combine",
    )):
        return "diagram"
    if any(word in lowered for word in (
        "api", "app", "interface", "dashboard", "software", "code", "screen",
        "click", "browser", "database",
    )):
        return "ui_mock"
    if any(word in lowered for word in (
        "gpu", "cpu", "chip", "processor", "device", "laptop", "phone",
        "hardware", "server", "product",
    )):
        if any(entity["type"] in ("company", "product") for entity in entities):
            return "official_media"
        return "stock_image"
    if any(word in lowered for word in (
        "factory", "manufactur", "assembl", "ship", "warehouse", "worker",
        "people", "pour", "build", "operat", "produce", "robot",
    )):
        return "stock_footage"
    if any(word in lowered for word in (
        "like", "as if", "imagine", "metaphor", "think of", "analogy", "chef",
    )):
        return "illustration"
    if any(word in lowered for word in (
        "system", "because", "why", "how", "model", "agent", "bottleneck",
    )):
        return "diagram"
    return "illustration"


def _concept_for(
    visual_type: str,
    entities: list[dict[str, Any]],
    narration: str,
    focus_word: str,
    scene_id: int,
) -> str:
    """Compose a single clear sentence naming the concrete scene picture."""
    subject = entities[0]["name"] if entities and entities[0]["type"] != "none" else "the idea"
    detail = focus_word or " ".join(_tokens(narration)[:5]) or f"beat {scene_id}"
    templates = {
        "chart": f"A chart makes the {subject} numbers behind {detail} instantly readable",
        "diagram": f"A diagram reveals how {subject} works in {detail}",
        "ui_mock": f"A realistic interface shows {subject} acting on {detail}",
        "stock_image": f"A photograph captures the real {subject} tied to {detail}",
        "official_media": f"Official press imagery shows the {subject} behind {detail}",
        "stock_footage": f"Footage shows {subject} happening in the real world during {detail}",
        "illustration": f"An illustration turns {subject} into a clear metaphor for {detail}",
    }
    sentence = templates.get(visual_type, templates["illustration"]) + "."
    return sentence[0].upper() + sentence[1:]


def _search_keywords(
    narration: str, entities: list[dict[str, Any]], focus_word: str, visual_type: str,
    topic_terms: list[str] | None = None,
) -> list[str]:
    """Build 2-6 specific, de-duplicated search terms for asset lookup."""
    candidates: list[str] = []
    # Topic-level nouns are the strongest anchors for a relevant image search.
    for word in (topic_terms or []):
        candidates.append(word)
    for entity in entities:
        for word in _tokens(entity["name"]):
            candidates.append(word)
    for word in _tokens(focus_word):
        candidates.append(word)
    for word in _tokens(narration):
        candidates.append(word)

    keywords: list[str] = []
    seen: set[str] = set()
    for word in candidates:
        if len(word) < 3 or word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        keywords.append(word)
    if not keywords:
        keywords = ["technology", "explainer"]
    for extra in (_STYLE_HINTS[visual_type].split(), ["close up", "high detail"]):
        for term in extra:
            if len(keywords) >= 6:
                break
            if term not in seen:
                seen.add(term)
                keywords.append(term)
    return keywords[:6]


def deterministic_visual_plan(topic: dict, script: dict, words: list[dict]) -> dict:
    """Build a semantic visual plan offline, with no network calls.

    Entity candidates come from the topic title/summary and each beat's
    narration via a keyword list; ``visual_type`` is chosen by content rules;
    narration spans come from word timings with a ``target_s`` fallback.  The
    returned plan always satisfies :func:`_validate`.
    """
    topic = topic or {}
    script = script or {}
    words = [word for word in (words or []) if isinstance(word, dict)]

    beats = _normalized_beats(script, topic)
    spans = _narration_spans(beats, words)

    topic_text = " ".join(
        _clean(topic.get(key)) for key in ("title", "summary", "hook")
    ).strip()
    topic_entities = _extract_entities(topic_text)

    scenes: list[dict[str, Any]] = []
    for index, beat in enumerate(beats):
        scene_id = index + 1
        narration = _clean(beat["narration"])
        entities = _extract_entities(f"{narration} {beat['focus_word']}", seed=topic_entities)
        visual_type = _classify_visual_type(f"{narration} {beat['focus_word']}", entities)

        concept = _concept_for(
            visual_type, entities, narration, beat["focus_word"], scene_id
        )
        topic_terms = _tokens(
            f"{topic.get('title', '')} {topic.get('summary', '')} {topic.get('topic', '')}"
        )
        keywords = _search_keywords(
            narration, entities, beat["focus_word"], visual_type, topic_terms
        )
        anchor = entities[0]["name"] if entities[0]["type"] != "none" else (beat["focus_word"] or keywords[0])
        query = _clean(
            f"{anchor} {' '.join(keywords[:3])} {_STYLE_HINTS[visual_type]}"
        )
        duration = _clamp_duration(spans[index]["end_s"] - spans[index]["start_s"])

        scenes.append({
            "scene_id": scene_id,
            "narration_span": spans[index],
            "main_visual_concept": concept,
            "entities": entities,
            "visual_type": visual_type,
            "asset_requirements": {
                "modality": (
                    "video" if visual_type == "stock_footage" else
                    "svg" if visual_type in ("illustration", "diagram") else
                    "markup" if visual_type in ("chart", "ui_mock") else "image"
                ),
                "query": query,
                "min_size": [1080, 1080] if visual_type in ("illustration", "diagram") else [1920, 1080],
                "avoid": ["generic abstract animation", "text overlays", "watermarks", "low resolution"],
            },
            "search_keywords": keywords,
            "camera": _CAMERA_BY_TYPE[visual_type],
            "animation": _ANIMATION_BY_TYPE[visual_type],
            "transition": _TRANSITION_CYCLE[index],
            "duration_s": duration,
            "fallback_strategy": _FALLBACK_BY_TYPE[visual_type],
            "relevance_assessed": True,
        })

    plan = {
        "topic": _clean(topic.get("title")) or _clean(script.get("title")) or "Untitled topic",
        "source": "deterministic",
        "scenes": scenes,
    }
    return plan


# ---------------------------------------------------------------------------
# Gemini-backed primary path.
# ---------------------------------------------------------------------------
def _prompt(topic: dict, script: dict) -> str:
    """Build the visual-director prompt from the topic and validated script."""
    topic_payload = {
        "title": str(topic.get("title") or ""),
        "summary": str(topic.get("summary") or ""),
        "hook": str(topic.get("hook") or ""),
        "pillar": str(topic.get("pillar") or ""),
        "entities": topic.get("entities") or [],
    }
    beats_payload: list[dict[str, Any]] = []
    for beat in (script.get("beats") or []):
        if isinstance(beat, dict):
            beats_payload.append({
                "id": str(beat.get("id") or ""),
                "label": str(beat.get("label") or ""),
                "focus_word": str(beat.get("focus_word") or ""),
                "lines": [str(x) for x in (beat.get("lines") or [])][:2],
                "narration": str(beat.get("narration") or "")[:240],
                "target_s": beat.get("target_s"),
            })

    return f"""You are the visual director for a 45-second tech Short that must be understandable with the sound OFF. For each narration beat, identify the real products, companies, people, physical objects, software interfaces, concepts, or statistics it is about, and choose the single visual_type that best depicts that subject.

TOPIC:
{json.dumps(topic_payload, ensure_ascii=False)}

SCRIPT BEATS (7, in order; narration is a fact anchor, never copy it verbatim):
{json.dumps(beats_payload, ensure_ascii=False)}

VISUAL_TYPE RULES:
- official_media: ONLY well-known named products with clear press imagery (a specific GPU, phone, robot, or device from a named company). Never for generic objects.
- stock_footage: real-world processes and actions (factory lines, people working, chips being manufactured).
- diagram: mechanisms, flows, pipelines, system architecture, "how it works".
- chart: numbers, percentages, benchmarks, comparisons, statistics.
- ui_mock: software, apps, APIs, dashboards, interfaces, code.
- illustration: metaphors, analogies, and abstract ideas with no literal subject.
- stock_image: a concrete physical product or object with no clear press imagery.
Never reuse a generic abstract animation as a scene identity: every scene must be about its own concrete subject.

For EACH of the 7 beats output one object with EXACTLY these keys:
- "main_visual_concept": one clear sentence describing the concrete picture for this beat.
- "entities": array of {{"name": str, "type": one of product|company|person|physical_object|software|concept|metric|none, "confidence": float 0..1}}. Include the real subjects; use "none" only when there is truly no depictable subject.
- "visual_type": one of stock_image|stock_footage|illustration|diagram|chart|ui_mock|official_media.
- "asset_requirements": {{"modality": one of image|video|svg|markup, "query": a specific asset search phrase, "min_size": [positive_int_width, positive_int_height], "avoid": array of short strings to avoid}}.
- "search_keywords": 2-6 specific search terms (never generic words like "technology" alone).
- "camera": one of dolly_in|zoom_out|pan_right|static_push.
- "animation": one of slow_push|flow_packet|count_up|reveal_layers|morph|parallax|none.
- "transition": one of wipe|zoom|morph|cut.
- "fallback_strategy": one of illustration|diagram|ui_mock|none.

Return ONLY a raw JSON object with this exact shape:
{{
  "scenes": [
    {{ ...seven objects, in the SAME order as the script beats... }}
  ]
}}"""


def _parse_response(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from a model reply, tolerating code fences."""
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


def _coerce_enum(value: Any) -> str:
    """Lowercase/strip a categorical value; invalid values fail validation."""
    return str(value or "").strip().lower()


def _coerce_entities(value: Any) -> list[dict[str, Any]]:
    """Coerce a model entity array; an empty/malformed array means 'none'."""
    entities: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            try:
                confidence: Any = float(item.get("confidence"))
            except (TypeError, ValueError):
                confidence = -1.0
            entities.append({
                "name": _clean(item.get("name")),
                "type": _coerce_enum(item.get("type")),
                "confidence": confidence,
            })
    return entities or [{"name": "none", "type": "none", "confidence": 1.0}]


def _normalize(
    data: dict[str, Any], model: str, topic: dict, script: dict, words: list[dict]
) -> dict[str, Any]:
    """Coerce a validated AI payload into the exact public plan shape."""
    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list) or len(raw_scenes) != 7:
        return {"topic": "", "source": "gemini:invalid", "scenes": []}

    beats = _normalized_beats(script, topic)
    spans = _narration_spans(beats, words)
    scenes: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_scenes):
        if not isinstance(raw, dict):
            return {"topic": "", "source": "gemini:invalid", "scenes": []}
        asset = raw.get("asset_requirements")
        asset = asset if isinstance(asset, dict) else {}
        size = asset.get("min_size")
        keywords = [str(word).strip() for word in (raw.get("search_keywords") or []) if str(word).strip()]
        avoid = [str(item) for item in (asset.get("avoid") or [])]
        duration = _clamp_duration(spans[index]["end_s"] - spans[index]["start_s"])
        scenes.append({
            "scene_id": index + 1,
            "narration_span": spans[index],
            "main_visual_concept": _clean(raw.get("main_visual_concept"))[:200],
            "entities": _coerce_entities(raw.get("entities")),
            "visual_type": _coerce_enum(raw.get("visual_type")),
            "asset_requirements": {
                "modality": _coerce_enum(asset.get("modality")),
                "query": _clean(asset.get("query")),
                "min_size": size if isinstance(size, list) else [],
                "avoid": avoid,
            },
            "search_keywords": keywords,
            "camera": _coerce_enum(raw.get("camera")),
            "animation": _coerce_enum(raw.get("animation")),
            "transition": _coerce_enum(raw.get("transition")),
            "duration_s": duration,
            "fallback_strategy": (
                str(raw.get("fallback_strategy") or "").strip().lower()
                if str(raw.get("fallback_strategy") or "").strip().lower() in FALLBACKS
                else _FALLBACK_BY_TYPE.get(
                    _coerce_enum(raw.get("visual_type")), "illustration"
                )
            ),
            "relevance_assessed": True,
        })
    return {
        "topic": _clean(topic.get("title")) or _clean(script.get("title")) or "Untitled topic",
        "source": f"gemini:{model}",
        "scenes": scenes,
    }


def build_visual_plan(topic: dict, script: dict, words: list[dict]) -> dict | None:
    """Return a validated, Gemini-generated semantic visual plan, or ``None``.

    The configured model is tried first, then two flash-lite fallbacks.  A
    candidate is accepted only when :func:`_validate` passes; a network error
    or a rejected candidate simply advances to the next model.  ``None`` is
    returned only when every model has failed, so the caller can fall back to
    :func:`deterministic_visual_plan`.
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
        models = list(dict.fromkeys([model for model in models if model]))
        prompt = _prompt(topic or {}, script or {})
    except Exception as exc:
        print(f"[VisualPlanner] setup failed: {exc}")
        return None

    for model in models:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            data = _parse_response(getattr(response, "text", ""))
            if not data:
                print(f"[VisualPlanner] {model} returned no JSON")
                continue
            plan = _normalize(data, model, topic or {}, script or {}, words or [])
            error = _validate(plan)
            if error:
                print(f"[VisualPlanner] {model} rejected: {error}")
                continue
            print(f"[VisualPlanner] built a semantic visual plan with {model}")
            return plan
        except Exception as exc:
            print(f"[VisualPlanner] {model} failed: {exc}")
            continue
    return None


# ---------------------------------------------------------------------------
# Offline self-test: python -m src.visual_planner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_beats = [
        ("hook", "GPU", "Your GPU renders 40 frames a second. That's the whole problem."),
        ("stake", "Nvidia", "Nvidia ships a new chip every year and the backlog never clears."),
        ("context", "API", "The API exposes a workflow that most apps never use."),
        ("mechanism", "CPU", "Each worker waits in a pipeline until the CPU frees up."),
        ("aha", "factory", "Inside the factory, robots assemble boards by hand in seconds."),
        ("payoff", "chef", "Think of it like a chef plating dishes at full speed."),
        ("loop", "model", "Now you can spot the bottleneck before it stalls your model."),
    ]
    script = {
        "title": "Why GPUs Are the Bottleneck",
        "beats": [
            {
                "id": beat_id,
                "label": beat_id.title(),
                "focus_word": focus,
                "lines": [narration],
                "narration": narration,
                "target_s": 6.0,
            }
            for beat_id, focus, narration in sample_beats
        ],
    }
    # Synthesize deterministic word timings from the narration, as voice.py would.
    word_list: list[dict] = []
    cursor = 0.0
    for _, _, narration in sample_beats:
        for token in narration.split():
            word_list.append({
                "text": token,
                "start": round(cursor, 3),
                "end": round(cursor + 0.3, 3),
            })
            cursor += 0.35

    plan = deterministic_visual_plan({"title": script["title"]}, script, word_list)
    assert _validate(plan) is None, _validate(plan)
    assert len(plan["scenes"]) == 7
    assert len({s["main_visual_concept"] for s in plan["scenes"]}) == 7
    print("[VisualPlanner] self-test passed: deterministic plan is schema-valid")
