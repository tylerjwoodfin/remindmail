import tempfile
import unittest
from datetime import date

import yaml

from remind.reminder import Reminder, ReminderKeyType


class _FakeCabinet:
    def log(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None

    def logdb(self, *args, **kwargs):
        return None


class _FakeMail:
    def send(self, *args, **kwargs):
        return None


class DayOfMonthReminderTests(unittest.TestCase):
    def _build_reminder(self, path_remind_file: str, value: str) -> Reminder:
        return Reminder(
            key=ReminderKeyType.DAY_OF_MONTH,
            title="Check statements",
            value=value,
            frequency=None,
            starts_on=None,
            offset=0,
            delete=False,
            command="",
            notes="",
            index=0,
            cabinet=_FakeCabinet(),
            mail=_FakeMail(),
            path_remind_file=path_remind_file,
        )

    def test_day_of_month_matches_when_value_is_string(self):
        reminder = self._build_reminder("/tmp/remindmail.yml", "15")

        self.assertTrue(reminder.get_should_send_today(target_date=date(2026, 4, 15)))
        self.assertFalse(reminder.get_should_send_today(target_date=date(2026, 4, 16)))

    def test_write_to_file_persists_day_of_month_as_integer(self):
        with tempfile.NamedTemporaryFile(suffix=".yml") as remind_file:
            reminder = self._build_reminder(remind_file.name, "15")

            reminder.write_to_file()

            remind_file.seek(0)
            data = yaml.safe_load(remind_file.read()) or {}

        self.assertEqual(
            data,
            {"reminders": [{"name": "Check statements", "dom": 15}]},
        )


if __name__ == "__main__":
    unittest.main()
