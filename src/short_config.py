"""Shared constants for the detailed short-form pipeline.

One source of truth for beat count, word budget and pacing so the script
writer, deterministic composer, storyboard director and renderer never drift.
"""
from __future__ import annotations

SHORT_BEATS = 12
SHORT_WORD_MIN = 180
SHORT_WORD_TARGET = 245
SHORT_WORD_MAX = 380
SHORT_MAX_SENTENCE_WORDS = 18
SHORT_WPM = 145

# Narrative arc for a detailed ~100-second short.
BEAT_IDS = [
    "hook",
    "stake",
    "context",
    "friction",
    "mechanism_1",
    "mechanism_2",
    "example",
    "aha",
    "tradeoff",
    "payoff",
    "proof",
    "loop",
]

LABELS = {
    "hook": "The Hook",
    "stake": "Why It Matters",
    "context": "The Setup",
    "friction": "The Friction",
    "mechanism_1": "Step One",
    "mechanism_2": "Step Two",
    "example": "A Real Example",
    "aha": "The Surprise",
    "tradeoff": "The Tradeoff",
    "payoff": "Your Move",
    "proof": "The Proof",
    "loop": "The Loop",
}

FOCUS_WORDS = {
    "hook": "the problem",
    "stake": "the stakes",
    "context": "the setup",
    "friction": "the friction",
    "mechanism_1": "step one",
    "mechanism_2": "step two",
    "example": "an example",
    "aha": "the surprise",
    "tradeoff": "the tradeoff",
    "payoff": "your move",
    "proof": "the proof",
    "loop": "one thing",
}

TARGET_S = {
    "hook": 4.0,
    "stake": 6.0,
    "context": 8.0,
    "friction": 7.0,
    "mechanism_1": 10.0,
    "mechanism_2": 10.0,
    "example": 9.0,
    "aha": 8.0,
    "tradeoff": 8.0,
    "payoff": 9.0,
    "proof": 9.0,
    "loop": 7.0,
}
