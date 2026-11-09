import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src import automation_daemon
from src.studio_engine import StudioEngine
from main import _run_scheduled_explainer, _run_scheduled_reels, _run_scheduled_reels_result


class AutomationTaskTests(unittest.TestCase):
    def setUp(self):
        automation_daemon.schedule.clear()
        self.daemon = automation_daemon.AutomationDaemon(dry_run=True)
        self.log_dir = tempfile.TemporaryDirectory()
        self.log_file = Path(self.log_dir.name) / "automation.log"
        self.log_patch = patch.object(automation_daemon, "LOG_FILE", self.log_file)
        self.log_patch.start()

    def tearDown(self):
        self.log_patch.stop()
        self.log_dir.cleanup()
        automation_daemon.schedule.clear()

    @patch("src.automation_daemon.subprocess.run")
    def test_one_shot_task_runs_main_action_in_dry_run_mode(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="completed", stderr="")

        self.assertTrue(self.daemon._run_pipeline("schedule-reels-shorts", 600))
        command = run.call_args.args[0]
        self.assertEqual(command[1], str(automation_daemon.BASE_DIR / "main.py"))
        self.assertEqual(command[2:], ["schedule-reels-shorts", "--dry-run"])
        self.assertIn("Succeeded", self.log_file.read_text(encoding="utf-8"))

    @patch("src.automation_daemon.subprocess.run")
    def test_one_shot_task_reports_nonzero_exit(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="publish failed")

        self.assertFalse(self.daemon._run_pipeline("schedule-explainer", 900))
        log = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Failed (exit code 1)", log)
        self.assertIn("publish failed", log)


class ExplainerScheduleTests(unittest.TestCase):
    def setUp(self):
        self.engine = StudioEngine.__new__(StudioEngine)
        self.now = datetime(2026, 11, 9, 12, 0)
        self.clock_patch = patch.object(StudioEngine, "_ist_now", return_value=self.now)
        self.clock_patch.start()

    def tearDown(self):
        self.clock_patch.stop()

    def test_explainer_requires_two_calendar_days_since_last_post(self):
        self.engine.history = {
            "events": [{"type": "explainer_video", "time": "2026-11-07 09:15 PM"}]
        }
        self.assertTrue(self.engine.is_alternate_day_for_explainer())

        self.engine.history["events"][0]["time"] = "2026-11-08 09:15 PM"
        self.assertFalse(self.engine.is_alternate_day_for_explainer())

    def test_invalid_last_explainer_timestamp_fails_closed(self):
        self.engine.history = {
            "events": [{"type": "explainer_video", "time": "not-a-date"}]
        }
        self.assertIsNone(self.engine.is_alternate_day_for_explainer())

    def test_no_previous_explainer_allows_first_run(self):
        self.engine.history = {"events": []}
        self.assertTrue(self.engine.is_alternate_day_for_explainer())

    def test_missing_render_output_is_not_treated_as_current_directory(self):
        self.assertIsNone(StudioEngine._rendered_video_path({}, "test"))

    def test_directory_is_rejected_as_rendered_video(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(
                StudioEngine._rendered_video_path({"video_path": directory}, "test")
            )

    def test_file_is_accepted_as_rendered_video(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "short.mp4"
            video.write_bytes(b"video")
            self.assertEqual(
                StudioEngine._rendered_video_path({"video_path": str(video)}, "test"),
                video,
            )


class ScheduledCliResultTests(unittest.TestCase):
    def test_partial_reels_broadcast_is_failure(self):
        class FakeEngine:
            def run_studio_all(self):
                return {"youtube": True, "instagram_reel": False}

        self.assertIsNone(_run_scheduled_reels(FakeEngine()))

    def test_all_reels_destinations_succeed(self):
        class FakeEngine:
            def run_studio_all(self):
                return {"youtube": True, "instagram_reel": True}

        self.assertIsNone(_run_scheduled_reels(FakeEngine()))

    def test_broadcast_with_only_threads_is_not_a_video_success(self):
        with self.assertRaises(SystemExit) as exc:
            _run_scheduled_reels_result({"threads": True})
        self.assertEqual(exc.exception.code, 1)

    def test_broadcast_without_any_video_platform_is_failure(self):
        with self.assertRaises(SystemExit) as exc:
            _run_scheduled_reels_result(
                {"youtube": False, "instagram_reel": False, "pinterest": False}
            )
        self.assertEqual(exc.exception.code, 1)

    def test_alternate_day_skip_is_not_a_failure(self):
        class FakeEngine:
            def run_long_explainer_slot(self):
                return {"published": False, "reason": "not_alternate_day"}

        self.assertIsNone(_run_scheduled_explainer(FakeEngine()))

    def test_expected_explainer_without_publish_is_failure(self):
        class FakeEngine:
            def run_long_explainer_slot(self):
                return {"published": False}

        with self.assertRaises(SystemExit) as exc:
            _run_scheduled_explainer(FakeEngine())
        self.assertEqual(exc.exception.code, 1)

    def test_invalid_explainer_history_is_failure(self):
        class FakeEngine:
            def run_long_explainer_slot(self):
                return {"published": False, "reason": "invalid_history"}

        with self.assertRaises(SystemExit) as exc:
            _run_scheduled_explainer(FakeEngine())
        self.assertEqual(exc.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
