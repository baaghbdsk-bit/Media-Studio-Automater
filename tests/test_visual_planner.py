"""Unit tests for the semantic visual planner.

Covers deterministic schema validity, strict enum/field validation (including
rejection of malformed plans), and narration-span coverage and ordering.
"""

import copy
import unittest

from src.visual_planner import (
    ANIMATIONS,
    CAMERAS,
    ENTITY_TYPES,
    FALLBACKS,
    MODALITIES,
    TRANSITIONS,
    VISUAL_TYPES,
    _validate,
    deterministic_visual_plan,
)


SAMPLE_BEATS = [
    ("hook", "GPU", "Your GPU renders 40 frames a second. That's the whole problem."),
    ("stake", "Nvidia", "Nvidia ships a new chip every year and the backlog never clears."),
    ("context", "API", "The API exposes a workflow that most apps never use."),
    ("mechanism", "CPU", "Each worker waits in a pipeline until the CPU frees up."),
    ("aha", "factory", "Inside the factory, robots assemble boards by hand in seconds."),
    ("payoff", "chef", "Think of it like a chef plating dishes at full speed."),
    ("loop", "model", "Now you can spot the bottleneck before it stalls your model."),
]


def _sample_script() -> dict:
    """Return a script with the seven beats expected by the planner."""
    return {
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
            for beat_id, focus, narration in SAMPLE_BEATS
        ],
    }


def _sample_words() -> list[dict]:
    """Synthesize monotonic word timings from the sample narration."""
    words: list[dict] = []
    cursor = 0.0
    for _, _, narration in SAMPLE_BEATS:
        for token in narration.split():
            words.append({"text": token, "start": round(cursor, 3), "end": round(cursor + 0.3, 3)})
            cursor += 0.35
    return words


class DeterministicPlanTests(unittest.TestCase):
    """The offline planner must always produce a valid semantic plan."""

    def setUp(self):
        self.topic = {"title": "Why GPUs Are the Bottleneck", "summary": "GPUs and chips."}
        self.script = _sample_script()
        self.words = _sample_words()
        self.plan = deterministic_visual_plan(self.topic, self.script, self.words)

    def test_plan_passes_strict_validation(self):
        self.assertIsNone(_validate(self.plan))

    def test_plan_shape_and_source(self):
        self.assertEqual(self.plan["source"], "deterministic")
        self.assertTrue(self.plan["topic"])
        self.assertEqual(len(self.plan["scenes"]), 7)
        self.assertEqual([s["scene_id"] for s in self.plan["scenes"]], list(range(1, 8)))

    def test_all_enums_and_required_types(self):
        for scene in self.plan["scenes"]:
            self.assertIn(scene["visual_type"], VISUAL_TYPES)
            self.assertIn(scene["camera"], CAMERAS)
            self.assertIn(scene["animation"], ANIMATIONS)
            self.assertIn(scene["transition"], TRANSITIONS)
            self.assertIn(scene["fallback_strategy"], FALLBACKS)
            self.assertIs(scene["relevance_assessed"], True)
            self.assertIsInstance(scene["entities"], list)
            for entity in scene["entities"]:
                self.assertIn(entity["type"], ENTITY_TYPES)
                self.assertIsInstance(entity["name"], str)
                self.assertGreaterEqual(entity["confidence"], 0.0)
            asset = scene["asset_requirements"]
            self.assertIn(asset["modality"], MODALITIES)
            self.assertTrue(asset["query"])
            self.assertEqual(len(asset["min_size"]), 2)
            self.assertIsInstance(asset["avoid"], list)
            self.assertTrue(scene["main_visual_concept"].strip())
            self.assertTrue(all(isinstance(k, str) and k.strip() for k in scene["search_keywords"]))

    def test_concepts_are_unique(self):
        concepts = [s["main_visual_concept"] for s in self.plan["scenes"]]
        self.assertEqual(len(set(concepts)), 7)

    def test_visual_types_are_semantic_not_a_fixed_sequence(self):
        # Different beats resolve to different visual types based on content.
        types = {s["visual_type"] for s in self.plan["scenes"]}
        self.assertGreaterEqual(len(types), 3)

    def test_plan_is_deterministic(self):
        again = deterministic_visual_plan(self.topic, _sample_script(), _sample_words())
        self.assertEqual(self.plan, again)

    def test_missing_words_falls_back_to_target_s(self):
        plan = deterministic_visual_plan(self.topic, self.script, [])
        self.assertIsNone(_validate(plan))
        spans = [s["narration_span"] for s in plan["scenes"]]
        self.assertTrue(all(s["end_s"] > s["start_s"] for s in spans))


class NarrationSpanTests(unittest.TestCase):
    """Narration spans must be ordered, non-empty and within the timeline."""

    def setUp(self):
        self.words = _sample_words()
        self.plan = deterministic_visual_plan(
            {"title": "Why GPUs Are the Bottleneck"}, _sample_script(), self.words
        )
        self.spans = [scene["narration_span"] for scene in self.plan["scenes"]]

    def test_span_text_matches_beats_and_is_non_empty(self):
        for span, (_, _, narration) in zip(self.spans, SAMPLE_BEATS):
            self.assertEqual(span["text"], narration)
            self.assertTrue(span["text"].strip())

    def test_spans_are_ordered_and_non_overlapping(self):
        self.assertGreaterEqual(self.spans[0]["start_s"], 0.0)
        for index, span in enumerate(self.spans):
            self.assertGreater(span["end_s"], span["start_s"])
            if index:
                self.assertGreaterEqual(span["start_s"], self.spans[index - 1]["end_s"])

    def test_spans_are_covered_by_the_audio_timeline(self):
        audio_end = max(word["end"] for word in self.words)
        self.assertLessEqual(self.spans[0]["start_s"], audio_end)
        self.assertLessEqual(self.spans[-1]["end_s"], audio_end + 0.001)
        # The first span starts at the beginning of narration and the last one
        # reaches the end, so the beats cover the full spoken timeline.
        self.assertAlmostEqual(self.spans[0]["start_s"], 0.0, places=2)
        self.assertAlmostEqual(self.spans[-1]["end_s"], audio_end, places=1)


class StrictValidationTests(unittest.TestCase):
    """A single illegal field must cause the plan to be rejected."""

    def setUp(self):
        self.plan = deterministic_visual_plan(
            {"title": "Why GPUs Are the Bottleneck"}, _sample_script(), _sample_words()
        )
        self.assertIsNone(_validate(self.plan))

    def _reject(self, mutate) -> None:
        bad = copy.deepcopy(self.plan)
        mutate(bad)
        self.assertIsNotNone(_validate(bad))

    def test_rejects_bad_visual_type(self):
        self._reject(lambda plan: plan["scenes"][0].update(visual_type="generic_animation"))

    def test_rejects_bad_camera(self):
        self._reject(lambda plan: plan["scenes"][1].update(camera="orbit"))

    def test_rejects_bad_animation(self):
        self._reject(lambda plan: plan["scenes"][2].update(animation="spin"))

    def test_rejects_bad_transition(self):
        self._reject(lambda plan: plan["scenes"][3].update(transition="dissolve"))

    def test_rejects_bad_modality(self):
        self._reject(
            lambda plan: plan["scenes"][0]["asset_requirements"].update(modality="gif")
        )

    def test_rejects_bad_entity_type(self):
        self._reject(lambda plan: plan["scenes"][0]["entities"][0].update(type="alien"))

    def test_rejects_wrong_scene_count(self):
        self._reject(lambda plan: plan.update(scenes=plan["scenes"][:-1]))

    def test_rejects_non_sequential_ids(self):
        self._reject(lambda plan: plan["scenes"][4].update(scene_id=4))

    def test_rejects_bad_duration(self):
        self._reject(lambda plan: plan["scenes"][0].update(duration_s=30.0))

    def test_rejects_empty_narration_text(self):
        self._reject(lambda plan: plan["scenes"][0]["narration_span"].update(text=""))

    def test_rejects_keyword_count(self):
        self._reject(lambda plan: plan["scenes"][0].update(search_keywords=["one"]))

    def test_rejects_duplicate_concept(self):
        def mutate(plan):
            plan["scenes"][1]["main_visual_concept"] = plan["scenes"][0]["main_visual_concept"]
        self._reject(mutate)

    def test_rejects_missing_relevance(self):
        self._reject(lambda plan: plan["scenes"][0].update(relevance_assessed=False))

    def test_rejects_non_object_plan(self):
        self.assertIsNotNone(_validate({"not": "a plan"}))


if __name__ == "__main__":
    unittest.main()
