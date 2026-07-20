"""Tests for annual February 29 handling (TJW-304)."""

import tempfile
import unittest
from datetime import date

import yaml

from remind.error_handler import ErrorHandler
from remind.query_manager import QueryManager
from remind.reminder import Reminder, ReminderKeyType
from unittest.mock import MagicMock


class _FakeCabinet:
    def log(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None


class _FakeMail:
    def send(self, *args, **kwargs):
        return None


class Feb29AnnualTests(unittest.TestCase):
    def setUp(self):
        manager = MagicMock()
        manager.cabinet = _FakeCabinet()
        manager.mail = _FakeMail()
        manager.remind_path_file = "/tmp/remindmail.yml"
        self.query = QueryManager(manager)

    def test_is_valid_date_accepts_02_29(self):
        self.assertTrue(ErrorHandler().is_valid_date("02-29"))
        self.assertEqual(ErrorHandler.parse_mm_dd("02-29"), (2, 29))

    def test_parse_every_february_29(self):
        reminder = self.query.interpret_reminder_date("every february 29")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertEqual(reminder.value, "02-29")
        self.assertFalse(reminder.delete)

    def test_write_to_file_persists_02_29(self):
        with tempfile.NamedTemporaryFile(suffix=".yml") as remind_file:
            reminder = Reminder(
                key=ReminderKeyType.DATE,
                title="Leap day",
                value="02-29",
                frequency=None,
                starts_on=None,
                offset=0,
                delete=False,
                command="",
                notes="",
                index=0,
                cabinet=_FakeCabinet(),
                mail=_FakeMail(),
                path_remind_file=remind_file.name,
            )
            reminder.write_to_file()
            remind_file.seek(0)
            data = yaml.safe_load(remind_file.read()) or {}

        self.assertEqual(
            data,
            {"reminders": [{"name": "Leap day", "date": "02-29"}]},
        )

    def test_sends_on_feb_29_in_leap_year(self):
        reminder = Reminder(
            key=ReminderKeyType.DATE,
            title="Leap day",
            value="02-29",
            frequency=None,
            starts_on=None,
            offset=0,
            delete=False,
            command="",
            notes="",
            index=0,
            cabinet=_FakeCabinet(),
            mail=_FakeMail(),
            path_remind_file="/tmp/remindmail.yml",
        )
        self.assertTrue(reminder.get_should_send_today(target_date=date(2024, 2, 29)))
        self.assertFalse(reminder.get_should_send_today(target_date=date(2024, 2, 28)))

    def test_sends_on_feb_28_in_non_leap_year(self):
        reminder = Reminder(
            key=ReminderKeyType.DATE,
            title="Leap day",
            value="02-29",
            frequency=None,
            starts_on=None,
            offset=0,
            delete=False,
            command="",
            notes="",
            index=0,
            cabinet=_FakeCabinet(),
            mail=_FakeMail(),
            path_remind_file="/tmp/remindmail.yml",
        )
        self.assertTrue(reminder.get_should_send_today(target_date=date(2025, 2, 28)))
        self.assertFalse(reminder.get_should_send_today(target_date=date(2025, 3, 1)))


if __name__ == "__main__":
    unittest.main()
