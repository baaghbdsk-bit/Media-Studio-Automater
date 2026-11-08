import unittest
from pathlib import Path
from src.studio_engine import StudioEngine

class StudioEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = StudioEngine(dry_run=True)

    def test_get_fresh_topic(self):
        topic = self.engine.get_fresh_topic()
        self.assertIsInstance(topic, dict)
        self.assertIn("title", topic)
        self.assertTrue(len(topic["title"]) > 0)

    def test_dry_run_studio_all(self):
        results = self.engine.run_studio_all()
        self.assertTrue(results.get("youtube"))
        self.assertTrue(results.get("instagram_reel"))
        self.assertTrue(results.get("threads"))
        self.assertTrue(results.get("pinterest"))

if __name__ == "__main__":
    unittest.main()
