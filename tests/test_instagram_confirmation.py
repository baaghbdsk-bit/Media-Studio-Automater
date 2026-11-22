import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from src.instagram_automater import InstagramAutomater


class _FakeBody:
    def __init__(self, text):
        self.text = text

    def inner_text(self, timeout=0):
        return self.text


class _FakeDialogs:
    def __init__(self, visible):
        self.visible = visible

    def count(self):
        return 1 if self.visible else 0

    def nth(self, index):
        return self

    def is_visible(self):
        return self.visible


class _FakePage:
    def __init__(self, body_text="", dialog_visible=False, url="https://www.instagram.com/"):
        self.body_text = body_text
        self.dialog_visible = dialog_visible
        self.url = url

    def locator(self, selector):
        if selector == "body":
            return _FakeBody(self.body_text)
        return _FakeDialogs(self.dialog_visible)

    def wait_for_timeout(self, milliseconds):
        pass


class InstagramConfirmationTests(unittest.TestCase):
    def test_confirmation_phrase_returns_true(self):
        page = _FakePage(body_text="Your reel has been shared.")
        self.assertTrue(InstagramAutomater()._await_share_confirmation(page, 1000))

    def test_closed_composer_without_confirmation_returns_false(self):
        # A composer closing on its own used to be counted as a successful publish,
        # which produced false "instagram_reel": true history entries.
        page = _FakePage(body_text="", dialog_visible=False)
        self.assertFalse(InstagramAutomater()._await_share_confirmation(page, 1000))

    def test_open_composer_without_confirmation_times_out(self):
        page = _FakePage(body_text="", dialog_visible=True)
        self.assertFalse(InstagramAutomater()._await_share_confirmation(page, 0))

    def test_generic_shared_word_is_not_a_confirmation(self):
        page = _FakePage(body_text="12 shares · Someone shared this post earlier")
        self.assertFalse(InstagramAutomater()._await_share_confirmation(page, 1000))

    def test_canonical_reel_url_is_a_confirmation(self):
        page = _FakePage(url="https://www.instagram.com/reel/DQm123abc/")
        automater = InstagramAutomater()
        self.assertTrue(automater._await_share_confirmation(page, 1000))
        self.assertEqual(automater.last_published_url, "https://www.instagram.com/reel/DQm123abc/")


class InstagramSessionValidationTests(unittest.TestCase):
    def _automater_with_cookies(self, cookies):
        with tempfile.TemporaryDirectory() as directory:
            cookie_file = Path(directory) / "cookies.json"
            cookie_file.write_text(json.dumps(cookies), encoding="utf-8")
            with patch("src.instagram_automater.config.BASE_DIR", Path(directory) / ".."):
                automater = InstagramAutomater()
                automater.user_data_dir = Path(directory)
                return automater.is_session_available()

    @staticmethod
    def _cookies(expires=-1):
        return [
            {"name": "sessionid", "value": "abc123", "domain": ".instagram.com", "expires": expires},
            {"name": "ds_user_id", "value": "12345", "domain": ".instagram.com", "expires": expires},
        ]

    def test_valid_auth_cookies_are_available(self):
        self.assertTrue(self._automater_with_cookies(self._cookies()))

    def test_expired_auth_cookies_are_rejected(self):
        self.assertFalse(self._automater_with_cookies(self._cookies(expires=time.time() - 60)))

    def test_missing_sessionid_is_rejected(self):
        cookies = [{"name": "ds_user_id", "value": "12345", "domain": ".instagram.com"}]
        self.assertFalse(self._automater_with_cookies(cookies))

    def test_empty_value_is_rejected(self):
        cookies = [
            {"name": "sessionid", "value": "", "domain": ".instagram.com"},
            {"name": "ds_user_id", "value": "12345", "domain": ".instagram.com"},
        ]
        self.assertFalse(self._automater_with_cookies(cookies))

    def test_no_cookie_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("src.instagram_automater.config.BASE_DIR", Path(directory) / ".."):
                automater = InstagramAutomater()
                automater.user_data_dir = Path(directory)
                self.assertFalse(automater.is_session_available())


if __name__ == "__main__":
    unittest.main()
