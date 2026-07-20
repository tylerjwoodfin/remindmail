"""Tests for RemindMail update-check emails (TJW-318)."""

import json
import unittest
from unittest.mock import MagicMock, patch

from remind.update_checker import (
    UpdateChecker,
    build_update_email,
    should_notify,
    _truthy,
)


class TruthyTests(unittest.TestCase):
    def test_none_defaults_true(self):
        self.assertTrue(_truthy(None))

    def test_false_values(self):
        for value in (False, 0, "false", "False", "no", "off", ""):
            self.assertFalse(_truthy(value), msg=repr(value))

    def test_true_values(self):
        for value in (True, 1, "true", "yes"):
            self.assertTrue(_truthy(value), msg=repr(value))


class ShouldNotifyTests(unittest.TestCase):
    def test_newer_version_notifies(self):
        self.assertTrue(should_notify("1!3.4.1", "1!4.0.0", None))

    def test_same_version_skips(self):
        self.assertFalse(should_notify("1!4.0.0", "1!4.0.0", None))

    def test_older_latest_skips(self):
        self.assertFalse(should_notify("1!4.0.0", "1!3.4.0", None))

    def test_already_notified_skips(self):
        self.assertFalse(should_notify("1!3.4.1", "1!4.0.0", "1!4.0.0"))

    def test_newer_than_last_notified_sends(self):
        self.assertTrue(should_notify("1!3.4.1", "1!4.1.0", "1!4.0.0"))

    def test_invalid_versions_skip(self):
        self.assertFalse(should_notify("not-a-version", "1!4.0.0", None))


class BuildUpdateEmailTests(unittest.TestCase):
    def test_subject_strips_epoch(self):
        subject, body = build_update_email("1!4.0.0", "1!3.4.1")
        self.assertEqual(subject, "🎉 RemindMail 4.0.0 Released")
        self.assertIn("pip install -U remindmail", body)
        self.assertIn("3.4.1", body)
        self.assertIn("4.0.0", body)


class UpdateCheckerTests(unittest.TestCase):
    def setUp(self):
        self.cabinet = MagicMock()
        self.mail = MagicMock()
        self.store = {}

        def fake_get(*keys, **kwargs):
            path = ".".join(str(k) for k in keys)
            return self.store.get(path)

        def fake_put(*keys, value=None, **kwargs):
            path = ".".join(str(k) for k in keys)
            self.store[path] = value

        self.cabinet.get.side_effect = fake_get
        self.cabinet.put.side_effect = fake_put
        self.cabinet.log = MagicMock()
        self.checker = UpdateChecker(self.cabinet, self.mail)

    @patch("remind.update_checker.fetch_latest_pypi_version", return_value="1!4.0.0")
    @patch("remind.update_checker.get_installed_version", return_value="1!3.4.1")
    def test_sends_once_and_records_version(self, _installed, _latest):
        self.assertTrue(self.checker.check_and_notify())
        self.mail.send.assert_called_once()
        subject = self.mail.send.call_args[0][0]
        self.assertEqual(subject, "🎉 RemindMail 4.0.0 Released")
        self.assertEqual(self.store["remindmail.last_notified_version"], "1!4.0.0")

        self.mail.send.reset_mock()
        self.assertFalse(self.checker.check_and_notify())
        self.mail.send.assert_not_called()

    @patch("remind.update_checker.fetch_latest_pypi_version", return_value="1!4.0.0")
    @patch("remind.update_checker.get_installed_version", return_value="1!3.4.1")
    def test_disabled_via_cabinet(self, _installed, _latest):
        self.store["remindmail.update-checks"] = False
        self.assertFalse(self.checker.check_and_notify())
        self.mail.send.assert_not_called()

    @patch("remind.update_checker.fetch_latest_pypi_version", return_value="1!4.0.0")
    @patch("remind.update_checker.get_installed_version", return_value="1!3.4.1")
    def test_dry_run_does_not_send_or_record(self, _installed, _latest):
        self.assertTrue(self.checker.check_and_notify(is_dry_run=True))
        self.mail.send.assert_not_called()
        self.assertNotIn("remindmail.last_notified_version", self.store)

    @patch("remind.update_checker.urllib.request.urlopen")
    def test_fetch_latest_parses_pypi_json(self, mock_urlopen):
        payload = json.dumps({"info": {"version": "1!4.0.0"}}).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.read.return_value = payload
        # json.load reads via the file-like object
        from io import BytesIO

        mock_cm.__enter__.return_value = BytesIO(payload)
        mock_urlopen.return_value = mock_cm

        from remind.update_checker import fetch_latest_pypi_version

        self.assertEqual(fetch_latest_pypi_version(), "1!4.0.0")


if __name__ == "__main__":
    unittest.main()
