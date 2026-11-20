import os
import tempfile
import unittest
from datetime import date

import yaml
from rich.console import Console

from remind.reminder_manager import ReminderManager


class _FakeCabinet:
    def log(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None


class _FakeMail:
    """Mimics Cabinet's Mail.send(), which returns False instead of raising."""

    def __init__(self, failing_titles: set[str]):
        self.failing_titles = failing_titles

    def send(self, subject, *args, **kwargs):
        return not any(subject.endswith(title) for title in self.failing_titles)


class DeleteAfterSendTests(unittest.TestCase):
    def _run_generate(self, reminders: list[dict], failing_titles: set[str]) -> list:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "remindmail.yml")
            with open(path, "w", encoding="utf-8") as file:
                yaml.safe_dump({"reminders": reminders}, file)

            manager = ReminderManager.__new__(ReminderManager)
            manager.cabinet = _FakeCabinet()
            manager.mail = _FakeMail(failing_titles)
            manager.console = Console(quiet=True)
            manager.remind_path_file = path
            manager.parsed_reminders = []

            manager.generate(is_dry_run=False)

            with open(path, encoding="utf-8") as file:
                return [r["name"] for r in yaml.safe_load(file)["reminders"]]

    def test_failed_send_keeps_one_off_reminder(self):
        today = date.today().isoformat()
        remaining = self._run_generate(
            [
                {"name": "sent one-off", "date": today, "delete": True},
                {"name": "failed one-off", "date": today, "delete": True},
                {"name": "daily", "every": 1, "unit": "days"},
            ],
            failing_titles={"failed one-off"},
        )

        self.assertEqual(remaining, ["failed one-off", "daily"])

    def test_successful_sends_delete_one_offs(self):
        today = date.today().isoformat()
        remaining = self._run_generate(
            [
                {"name": "one-off", "date": today, "delete": True},
                {"name": "daily", "every": 1, "unit": "days"},
            ],
            failing_titles=set(),
        )

        self.assertEqual(remaining, ["daily"])


if __name__ == "__main__":
    unittest.main()
