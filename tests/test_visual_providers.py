"""Offline tests for the visual provider system. No live APIs are called."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.asset_cache import AssetCache
from src.license_ledger import LicenseLedger
from src.visual_providers import (
    ASSET_KEYS,
    DiagramProvider,
    FallbackProvider,
    IllustrationProvider,
    OfficialMediaProvider,
    StockProvider,
    UiMockProvider,
    make_asset,
)
from src.visual_providers import orchestrator as orch
from src.visual_providers.stock_provider import OPENVERSE_API, WIKIMEDIA_API

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-payload"


class FakeResponse:
    """Minimal requests.Response stand-in used by all offline tests."""

    def __init__(self, status_code=200, headers=None, payload=None, body=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload
        self._body = body

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def iter_content(self, chunk_size=8192):
        for offset in range(0, len(self._body), chunk_size):
            yield self._body[offset : offset + chunk_size]


def image_response(body=PNG):
    return FakeResponse(headers={"Content-Type": "image/png"}, body=body)


# --------------------------------------------------------------------------- #
# License ledger
# --------------------------------------------------------------------------- #
class LicenseLedgerTests(unittest.TestCase):
    def test_allowed_and_rejected_licenses(self):
        ledger = LicenseLedger(root=tempfile.mkdtemp())
        allowed = [
            "CC0", "Public Domain", "CC BY 4.0", "CC BY-SA 4.0",
            "Pixabay Content License", "Pexels License", "MIT/Own-generated",
            "official press", "cc0", "pdm",  # Openverse 'by'/'by-sa' codes are normalized by StockProvider
        ]
        rejected = [
            "CC BY-NC 4.0", "CC BY-ND 4.0", "CC BY-NC-SA 4.0",
            "All Rights Reserved", "unknown", "", None,
            "<span>CC BY-NC</span>", "Proprietary",
        ]
        for value in allowed:
            self.assertTrue(ledger.accept({"license": value}), "should allow %r" % value)
        for value in rejected:
            self.assertFalse(ledger.accept({"license": value}), "should reject %r" % value)

    def test_normalize_and_attribution(self):
        ledger = LicenseLedger(root=tempfile.mkdtemp())
        self.assertEqual(ledger.normalize("<b>CC BY-SA</b> 4.0"), "CC BY-SA")
        self.assertEqual(ledger.normalize("cc-by-nc 4.0"), "")
        asset = make_asset(
            "stock", "image", source_url="https://example.org/a.png",
            license="CC BY 4.0", attribution="Photographer",
        )
        line = ledger.attribution_line(asset)
        self.assertIn("Photographer", line)
        self.assertIn("https://example.org/a.png", line)

    def test_write_persists_records(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = LicenseLedger(root=root)
            asset = make_asset("diagram", "markup", license="MIT/Own-generated", sha256="abc")
            self.assertTrue(ledger.record_asset(asset))
            self.assertTrue(ledger.record_asset(asset))  # deduped
            path = ledger.write()
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(len(data["records"]), 1)
            self.assertIn("CC0", data["allowed_licenses"])
            self.assertEqual(LicenseLedger(root=root).records[0]["sha256"], "abc")


# --------------------------------------------------------------------------- #
# Asset cache
# --------------------------------------------------------------------------- #
class AssetCacheTests(unittest.TestCase):
    def test_dedupe_get_and_local_path(self):
        with tempfile.TemporaryDirectory() as root:
            cache = AssetCache(root=root)
            first = cache.put_bytes("https://example.org/a.png", PNG, "png")
            second = cache.put_bytes("https://example.org/b.png", PNG, "png")
            self.assertEqual(first.name, second.name)
            self.assertEqual(cache.get("https://example.org/a.png"), PNG)
            self.assertEqual(cache.get("https://example.org/b.png"), PNG)
            self.assertEqual(cache.hash_bytes(PNG), hashlib.sha256(PNG).hexdigest())
            local = cache.local_path_for(first)
            self.assertTrue(local.startswith("assets/"))
            self.assertTrue((Path(root) / local).exists())

    def test_usage_history_and_was_used(self):
        with tempfile.TemporaryDirectory() as root:
            cache = AssetCache(root=root)
            asset = make_asset("stock", "image", sha256="hash-1")
            topic = {"id": "topic-42", "title": "Robots"}
            self.assertFalse(cache.was_used("hash-1", topic))
            cache.record_usage(asset, topic, 3)
            self.assertTrue(cache.was_used("hash-1", topic))
            self.assertFalse(cache.was_used("hash-1", {"id": "other"}))
            data = json.loads((Path(root) / "usage.json").read_text(encoding="utf-8"))
            self.assertEqual(data[0]["scene_id"], 3)
            self.assertEqual(len(cache.usage_history(topic)), 1)

    def test_select_prefers_unused_but_respects_relevance_gate(self):
        with tempfile.TemporaryDirectory() as root:
            cache = AssetCache(root=root)
            topic = {"id": "t1"}
            used_relevant = {"sha256": "used", "relevance_score": 0.9}
            fresh_low = {"sha256": "fresh-low", "relevance_score": 0.6}
            fresh_similar = {"sha256": "fresh-similar", "relevance_score": 0.88}
            cache.record_usage(make_asset(sha256="used"), topic, 1)
            chosen = cache.select([used_relevant, fresh_low, fresh_similar], topic, score_gate=0.05)
            self.assertEqual(chosen["sha256"], "fresh-similar")
            # Fresh but far less relevant must not beat the used relevant asset.
            chosen = cache.select([used_relevant, fresh_low], topic, score_gate=0.05)
            self.assertEqual(chosen["sha256"], "used")


# --------------------------------------------------------------------------- #
# Stock provider (stubbed HTTP)
# --------------------------------------------------------------------------- #
class StockProviderTests(unittest.TestCase):
    def test_rejects_disallowed_wikimedia_license_and_uses_openverse(self):
        def fake_get(url, **kwargs):
            if url == WIKIMEDIA_API:
                return FakeResponse(payload={
                    "query": {"pages": {"1": {
                        "title": "File:nope.png",
                        "imageinfo": [{
                            "thumburl": "https://img.example/nope.png",
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY-NC 4.0"},
                                "Artist": {"value": "Restricted Author"},
                            },
                        }],
                    }}},
                })
            if url == OPENVERSE_API:
                return FakeResponse(payload={"results": [{
                    "url": "https://img.example/openverse.png",
                    "thumbnail": "https://img.example/openverse.png",
                    "license": "cc0",
                    "title": "robot concept",
                    "creator": "Open Author",
                }]})
            if url.startswith("https://img.example/"):
                return image_response()
            raise AssertionError("unexpected URL %s" % url)

        with tempfile.TemporaryDirectory() as root:
            cache, ledger = AssetCache(root=root), LicenseLedger(root=root)
            with patch("requests.get", side_effect=fake_get):
                asset = StockProvider().resolve(
                    {"visual_type": "stock_image", "main_visual_concept": "robot concept"},
                    {"title": "Robots"}, cache, ledger,
                )
            self.assertIsNotNone(asset)
            self.assertEqual(asset["license"], "CC0")
            self.assertEqual(asset["provider"], "stock")
            self.assertIn("openverse.png", asset["source_url"])
            self.assertTrue(asset["local_path"].startswith("assets/"))
            self.assertEqual(asset["sha256"], hashlib.sha256(PNG).hexdigest())
            self.assertGreaterEqual(asset["relevance_score"], 0.7)

    def test_api_failure_returns_none_without_live_network(self):
        def fake_get(url, **kwargs):
            raise requests.Timeout("stubbed timeout")

        with tempfile.TemporaryDirectory() as root:
            with patch("requests.get", side_effect=fake_get):
                asset = StockProvider().resolve(
                    {"visual_type": "stock_image", "main_visual_concept": "robot"},
                    {"title": "Robots"}, AssetCache(root=root), LicenseLedger(root=root),
                )
            self.assertIsNone(asset)

    def test_pixabay_only_used_when_key_present(self):
        calls = []

        def fake_get(url, **kwargs):
            calls.append(url)
            if url == WIKIMEDIA_API or url == OPENVERSE_API:
                return FakeResponse(payload={})
            if url.startswith("https://pixabay.com/api/"):
                return FakeResponse(payload={"hits": [{
                    "webformatURL": "https://img.example/pixabay.png",
                    "user": "Pixabay User", "tags": "flowers",
                }]})
            return image_response()

        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {"PIXABAY_API_KEY": "test-key"}):
                with patch("requests.get", side_effect=fake_get):
                    asset = StockProvider().resolve(
                        {"visual_type": "stock_image", "main_visual_concept": "flowers"},
                        {"title": "Flowers"}, AssetCache(root=root), LicenseLedger(root=root),
                    )
            self.assertIsNotNone(asset)
            self.assertEqual(asset["license"], "Pixabay Content License")
            self.assertTrue(any("pixabay.com" in url for url in calls))


# --------------------------------------------------------------------------- #
# Official media provider (stubbed reachability)
# --------------------------------------------------------------------------- #
class OfficialMediaProviderTests(unittest.TestCase):
    def test_disabled_without_official_type_or_entity(self):
        provider = OfficialMediaProvider()
        self.assertFalse(provider.supports(
            {"visual_type": "stock_image", "main_visual_concept": "NVIDIA GPUs"},
            {"title": "NVIDIA"},
        ))
        self.assertFalse(provider.supports(
            {"visual_type": "official_media", "main_visual_concept": "random topic"},
            {"title": "Nothing"},
        ))
        self.assertTrue(provider.supports(
            {"visual_type": "official_media", "main_visual_concept": "NVIDIA GPUs"},
            {"title": "Chips"},
        ))

    def test_reachable_official_asset(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("requests.get", return_value=image_response()):
                asset = OfficialMediaProvider().resolve(
                    {"visual_type": "official_media", "entity": "openai",
                     "main_visual_concept": "OpenAI announcement"},
                    {"title": "AI news"}, AssetCache(root=root), LicenseLedger(root=root),
                )
            self.assertIsNotNone(asset)
            self.assertEqual(asset["license"], "official press")
            self.assertEqual(asset["provider"], "official_media")
            self.assertEqual(asset["relevance_score"], 0.95)


# --------------------------------------------------------------------------- #
# Markup providers
# --------------------------------------------------------------------------- #
class MarkupProviderTests(unittest.TestCase):
    def _asset(self, provider, scene):
        return provider.resolve(scene, {"title": "Systems"}, None, LicenseLedger(root=tempfile.mkdtemp()))

    def test_diagram_kinds_and_self_contained_markup(self):
        for visual_type, expected in (
            ("flow", "flow"), ("layers", "layers"), ("grid", "grid"),
            ("queue", "queue"), ("chart", "chart"), ("compare", "compare"),
        ):
            asset = self._asset(DiagramProvider(), {
                "visual_type": visual_type, "main_visual_concept": "data pipeline",
            })
            self.assertIsNotNone(asset)
            self.assertEqual(asset["type"], "markup")
            self.assertIn('data-diagram="%s"' % expected, asset["inline_markup"])
            self.assertIn("currentColor", asset["inline_markup"])
            # The only URL is the SVG XML namespace; no external resources.
            self.assertNotIn("<image", asset["inline_markup"])
            self.assertNotIn("src=", asset["inline_markup"])
            self.assertNotIn("@import", asset["inline_markup"])

    def test_illustration_uses_icon_vocabulary(self):
        asset = self._asset(IllustrationProvider(), {
            "visual_type": "illustration", "icon": "cpu",
            "main_visual_concept": "AI model",
        })
        self.assertIsNotNone(asset)
        self.assertEqual(asset["type"], "markup")
        self.assertIn('data-icon="cpu"', asset["inline_markup"])
        self.assertIn("<svg", asset["inline_markup"])

    def test_ui_mock_templates(self):
        for visual_type, expected in (
            ("ui_mock", "browser"), ("terminal", "terminal"),
            ("dashboard", "dashboard"), ("chat", "chat"),
        ):
            asset = self._asset(UiMockProvider(), {
                "visual_type": visual_type, "main_visual_concept": "demo app",
            })
            self.assertIsNotNone(asset)
            self.assertIn('data-ui="%s"' % expected, asset["inline_markup"])
            self.assertIn("<style>", asset["inline_markup"])

    def test_fallback_never_empty(self):
        asset = self._asset(FallbackProvider(), {"visual_type": "unknown", "main_visual_concept": "x"})
        self.assertIsNotNone(asset)
        self.assertEqual(asset["type"], "markup")
        self.assertTrue(asset["inline_markup"])


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
class StubProvider:
    def __init__(self, name, asset=None, raises=False, supports=True):
        self.name = name
        self.asset = asset
        self.raises = raises
        self._supports = supports

    def supports(self, scene, topic):
        return self._supports

    def resolve(self, scene, topic, cache, ledger):
        if self.raises:
            raise RuntimeError("stubbed provider crash")
        return self.asset


PLAN = {
    "source": "unit-test",
    "scenes": [
        {
            "scene_id": 1,
            "narration_span": {"start": 0, "end": 3},
            "visual_type": "stock_image",
            "main_visual_concept": "a robot",
            "camera": "zoom-in", "animation": "pan", "transition": "fade",
            "duration_s": 3.5,
        },
        {
            "scene_id": 2,
            "narration_span": {},
            "visual_type": "diagram",
            "main_visual_concept": "data flow",
        },
    ],
}


class OrchestratorTests(unittest.TestCase):
    SCENE_KEYS = {
        "scene_id", "narration_span", "visual_type", "main_visual_concept",
        "asset", "camera", "animation", "transition", "duration_s",
        "fallback_strategy", "relevance_assessed",
    }

    def test_manifest_shape_with_real_markup_providers(self):
        providers = [DiagramProvider(), UiMockProvider(), IllustrationProvider(), FallbackProvider()]
        with tempfile.TemporaryDirectory() as root:
            with patch.object(orch, "_providers", return_value=providers):
                manifest = orch.resolve_plan(PLAN, {"id": "t1", "title": "Robots"}, cache_root=root)
            self.assertEqual(set(manifest.keys()), {"topic", "source", "scenes"})
            self.assertEqual(manifest["source"], "unit-test")
            self.assertEqual(len(manifest["scenes"]), 2)
            for scene in manifest["scenes"]:
                self.assertEqual(set(scene.keys()), self.SCENE_KEYS)
                self.assertTrue(scene["relevance_assessed"])
                self.assertEqual(set(scene["asset"].keys()), set(ASSET_KEYS))
                self.assertTrue(scene["asset"]["inline_markup"])
            self.assertEqual(manifest["scenes"][1]["asset"]["provider"], "diagram")
            self.assertTrue((Path(root) / "licenses.json").exists())
            self.assertTrue((Path(root) / "usage.json").exists())

    def test_fallback_chain_on_raise_and_license_rejection(self):
        crashing = StubProvider("crashing", raises=True)
        bad_license = StubProvider("bad-license", asset=make_asset(
            "stock", "image", license="CC BY-NC 4.0", sha256="bad", relevance_score=0.9,
        ))
        with tempfile.TemporaryDirectory() as root:
            with patch.object(orch, "_providers", return_value=[crashing, bad_license, FallbackProvider()]):
                manifest = orch.resolve_plan(PLAN, {"id": "t2"}, cache_root=root)
            for scene in manifest["scenes"]:
                self.assertEqual(scene["asset"]["provider"], "fallback")
                self.assertEqual(scene["asset"]["license"], "MIT/Own-generated")

    def test_first_valid_provider_wins_and_asset_reuse(self):
        good = make_asset(
            "stock", "image", license="CC0", sha256="reused-hash",
            local_path="assets/reused.png", relevance_score=0.75,
        )
        with tempfile.TemporaryDirectory() as root:
            with patch.object(orch, "_providers", return_value=[StubProvider("good", asset=good), FallbackProvider()]):
                manifest = orch.resolve_plan(PLAN, {"id": "t3"}, cache_root=root)
            hashes = [s["asset"]["sha256"] for s in manifest["scenes"]]
            self.assertEqual(hashes, ["reused-hash", "reused-hash"])
            self.assertEqual(manifest["scenes"][0]["asset"]["relevance_score"], 0.75)

    def test_never_crashes_on_malformed_input(self):
        manifest = orch.resolve_plan({"scenes": [None, "bad", {}]}, "topic", cache_root=tempfile.mkdtemp())
        self.assertEqual(len(manifest["scenes"]), 3)
        for scene in manifest["scenes"]:
            self.assertEqual(set(scene["asset"].keys()), set(ASSET_KEYS))


if __name__ == "__main__":
    unittest.main()
