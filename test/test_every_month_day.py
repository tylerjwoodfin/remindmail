"""Tests for annual 'every <month> <day>' reminders (TJW-269)."""

import tempfile
import unittest
from datetime import date
from unittest.mock import MagicMock

import yaml

from remind.query_manager import QueryManager
from remind.reminder import Reminder, ReminderKeyType


class _FakeCabinet:
    def log(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None


class _FakeMail:
    def send(self, *args, **kwargs):
        return None


class EveryMonthDayTests(unittest.TestCase):
    def setUp(self):
        manager = MagicMock()
        manager.cabinet = _FakeCabinet()
        manager.mail = _FakeMail()
        manager.remind_path_file = "/tmp/remindmail.yml"
        self.query = QueryManager(manager)

    def test_parse_every_december_1(self):
        reminder = self.query.interpret_reminder_date("every december 1")

        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertEqual(reminder.value, "12-01")
        self.assertFalse(reminder.delete)

    def test_parse_every_dec_1st(self):
        reminder = self.query.interpret_reminder_date("every Dec 1st")

        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertEqual(reminder.value, "12-01")
        self.assertFalse(reminder.delete)

    def test_parse_every_july_4(self):
        reminder = self.query.interpret_reminder_date("every July 4")

        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertEqual(reminder.value, "07-04")
        self.assertFalse(reminder.delete)

    def test_parse_invalid_month_day_raises(self):
        with self.assertRaises(ValueError):
            self.query.interpret_reminder_date("every february 30")

    def test_annual_date_matches_each_year(self):
        reminder = Reminder(
            key=ReminderKeyType.DATE,
            title="Donate to Wikipedia",
            value="12-01",
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

        self.assertTrue(reminder.get_should_send_today(target_date=date(2026, 12, 1)))
        self.assertTrue(reminder.get_should_send_today(target_date=date(2027, 12, 1)))
        self.assertFalse(reminder.get_should_send_today(target_date=date(2026, 12, 2)))
        self.assertFalse(reminder.get_should_send_today(target_date=date(2026, 11, 30)))

    def test_write_to_file_persists_annual_mm_dd(self):
        with tempfile.NamedTemporaryFile(suffix=".yml") as remind_file:
            reminder = Reminder(
                key=ReminderKeyType.DATE,
                title="Donate to Wikipedia",
                value="12-01",
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
            {"reminders": [{"name": "Donate to Wikipedia", "date": "12-01"}]},
        )


if __name__ == "__main__":
    unittest.main()
