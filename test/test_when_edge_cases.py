"""Edge-case coverage for interpret_reminder_date (TJW-302)."""

import unittest
from unittest.mock import MagicMock

from remind.query_manager import QueryManager, _match_weekday_token
from remind.reminder import ReminderKeyType


class _FakeCabinet:
    def log(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None


class _FakeMail:
    def send(self, *args, **kwargs):
        return None


class ReminderWhenEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        manager = MagicMock()
        manager.cabinet = _FakeCabinet()
        manager.mail = _FakeMail()
        manager.remind_path_file = "/tmp/remindmail.yml"
        self.query = QueryManager(manager)

    def _parse(self, when: str):
        return self.query.interpret_reminder_date(when)

    # --- the months / Monday regression ---

    def test_every_month_is_monthly_not_monday(self):
        reminder = self._parse("every month")
        self.assertEqual(reminder.key, ReminderKeyType.MONTH)
        self.assertEqual(reminder.frequency, 1)
        self.assertFalse(reminder.delete)

    def test_every_3_months_is_monthly_not_monday(self):
        reminder = self._parse("every 3 months")
        self.assertEqual(reminder.key, ReminderKeyType.MONTH)
        self.assertEqual(reminder.frequency, 3)

    def test_every_2_months(self):
        reminder = self._parse("every 2 months")
        self.assertEqual(reminder.key, ReminderKeyType.MONTH)
        self.assertEqual(reminder.frequency, 2)

    def test_mon_not_matched_inside_months(self):
        self.assertIsNone(
            _match_weekday_token("every 3 months", {"mon": object(), "monday": object()})
        )

    # --- interval reminders ---

    def test_every_day(self):
        reminder = self._parse("every day")
        self.assertEqual(reminder.key, ReminderKeyType.DAY)
        self.assertEqual(reminder.frequency, 1)

    def test_every_2_days(self):
        reminder = self._parse("every 2 days")
        self.assertEqual(reminder.key, ReminderKeyType.DAY)
        self.assertEqual(reminder.frequency, 2)

    def test_every_week_becomes_sunday(self):
        reminder = self._parse("every week")
        self.assertEqual(reminder.key, ReminderKeyType.SUNDAY)
        self.assertEqual(reminder.frequency, 1)

    def test_every_2_weeks(self):
        reminder = self._parse("every 2 weeks")
        self.assertEqual(reminder.key, ReminderKeyType.WEEK)
        self.assertEqual(reminder.frequency, 2)

    # --- weekday reminders ---

    def test_every_monday(self):
        reminder = self._parse("every monday")
        self.assertEqual(reminder.key, ReminderKeyType.MONDAY)
        self.assertEqual(reminder.frequency, 1)

    def test_every_mon_abbrev(self):
        reminder = self._parse("every mon")
        self.assertEqual(reminder.key, ReminderKeyType.MONDAY)

    def test_every_3_mondays(self):
        reminder = self._parse("every 3 mondays")
        self.assertEqual(reminder.key, ReminderKeyType.MONDAY)
        self.assertEqual(reminder.frequency, 3)

    def test_every_friday(self):
        reminder = self._parse("every friday")
        self.assertEqual(reminder.key, ReminderKeyType.FRIDAY)

    def test_one_shot_friday_is_date(self):
        reminder = self._parse("friday")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertTrue(reminder.delete)
        self.assertRegex(str(reminder.value), r"^\d{4}-\d{2}-\d{2}$")

    # --- one-shot / special ---

    def test_tomorrow(self):
        reminder = self._parse("tomorrow")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertTrue(reminder.delete)

    def test_now(self):
        reminder = self._parse("now")
        self.assertEqual(reminder.key, ReminderKeyType.NOW)

    def test_later(self):
        reminder = self._parse("later")
        self.assertEqual(reminder.key, ReminderKeyType.LATER)
        self.assertFalse(reminder.delete)

    def test_day_of_month(self):
        reminder = self._parse("15")
        self.assertEqual(reminder.key, ReminderKeyType.DAY_OF_MONTH)
        self.assertEqual(reminder.value, "15")

    def test_the_15th(self):
        reminder = self._parse("the 15th")
        self.assertEqual(reminder.key, ReminderKeyType.DAY_OF_MONTH)
        self.assertEqual(reminder.value, "15")

    def test_specific_month_day(self):
        reminder = self._parse("december 1")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertRegex(str(reminder.value), r"^\d{4}-12-01$")
        self.assertTrue(reminder.delete)

    def test_mm_dd(self):
        reminder = self._parse("12/25")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertRegex(str(reminder.value), r"^\d{4}-12-25$")

    def test_yyyy_mm_dd_future(self):
        reminder = self._parse("2099-07-04")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertEqual(reminder.value, "2099-07-04")

    def test_yyyy_mm_dd_past_rolls_to_next_year(self):
        """Past calendar dates without an explicit future year roll forward one year."""
        reminder = self._parse("2020-01-01")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        # set_date_key_value advances past dates by one year from the proposed date
        self.assertEqual(reminder.value, "2021-01-01")

    def test_relative_in_3_days(self):
        reminder = self._parse("in 3 days")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertRegex(str(reminder.value), r"^\d{4}-\d{2}-\d{2}$")

    def test_relative_in_2_weeks(self):
        reminder = self._parse("in 2 weeks")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)

    def test_relative_in_2_months(self):
        """Relative 'in 2 months' must stay a one-shot date, not a weekday."""
        reminder = self._parse("in 2 months")
        self.assertEqual(reminder.key, ReminderKeyType.DATE)
        self.assertTrue(reminder.delete)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            self._parse("blargle")


if __name__ == "__main__":
    unittest.main()
