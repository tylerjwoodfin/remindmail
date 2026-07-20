"""
handles reminder requests
"""

import re
import sys
from typing import Tuple, Optional, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from remind.reminder import Reminder, ReminderKeyType
from remind.reminder_confirmation import ReminderConfirmation
from remind.reminder_manager import ReminderManager
from prompt_toolkit import print_formatted_text, HTML
from cabinet import Cabinet, Mail

# English month names / abbreviations → month number (avoids locale-dependent strptime %b).
_MONTH_NAME_TO_NUM: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _match_weekday_token(text: str, weekday_tokens: dict) -> str | None:
    """
    Return the longest weekday token found as a whole word in ``text``.

    Uses word boundaries so ``mon`` does not match inside ``months``.
    Longer tokens are preferred (``monday`` before ``mon``).
    """
    for day in sorted(weekday_tokens.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(day)}\b", text, flags=re.IGNORECASE):
            return day.lower()
    return None


class QueryManager:
    """
    handles reminder requests
    """

    def __init__(self, manager: ReminderManager) -> None:
        self.manager: ReminderManager = manager
        self.cabinet: Cabinet = self.manager.cabinet
        self.mail: Mail = self.manager.mail
        return

    def interpret_reminder_date(self, input_str: str) -> Reminder:
        """
        Parses a reminder date from a natural language string.

        The function supports various date formats, including relative dates (e.g., "in 3 weeks"),
        specific calendar dates (e.g., "July 4"), and weekdays (e.g., "Tuesday"). It interprets
        these formats to return a Reminder object with the calculated date.

        Parameters:
        - input_str (str): The input string containing the date information.

        Returns:
        - Reminder: An object representing the reminder with the interpreted date.

        Raises:
        - ValueError: If the input string cannot be parsed into a known date format.
        """

        def set_date_key_value(
            proposed_date: datetime,
            value: str,
            key: Optional[ReminderKeyType] = ReminderKeyType.DATE,
        ) -> Tuple[ReminderKeyType, str]:
            """
            Adjusts the proposed date if it's in the past
            and sets the appropriate key and value based on the date.

            If the reminder is for today, set the type to NOW if after 4AM.

            Args:
                proposed_date (datetime): The proposed date to be evaluated.
                key (Optional[ReminderKeyType]): The reminder key type to be set.
                    Defaults to ReminderKeyType.DATE.
                value (str): The reminder value to be set.

            Returns:
                tuple: A tuple containing the updated key and value.
            """
            if proposed_date < start_date:
                proposed_date += relativedelta(years=1)
            if proposed_date == start_date and now.hour >= 4:
                key = ReminderKeyType.NOW
            else:
                key = ReminderKeyType.DATE
                value = proposed_date.strftime("%Y-%m-%d")
            return key, value

        weekdays = {
            "monday": MO(+1),
            "mon": MO(+1),
            "tuesday": TU(+1),
            "tue": TU(+1),
            "wednesday": WE(+1),
            "wed": WE(+1),
            "thursday": TH(+1),
            "thu": TH(+1),
            "friday": FR(+1),
            "fri": FR(+1),
            "saturday": SA(+1),
            "sat": SA(+1),
            "sunday": SU(+1),
            "sun": SU(+1),
        }

        # Precompile regular expressions
        regex_patterns = {
            "relative": re.compile(
                r"(?:in )?(\d+) (day|week|month|year)s?(?: from now)?", re.IGNORECASE
            ),
            "day_of_month": re.compile(
                r"\b(?:the )?(\d{1,2})(st|nd|rd|th)?\b", re.IGNORECASE
            ),
            "every_weeks": re.compile(r"^every (\d+) weeks?$", re.IGNORECASE),
            "specific_date": re.compile(
                r"(?i)\b("
                r"january|february|march|april|may|june|july|august|"
                r"september|october|november|december|"
                r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
                r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,? (\d{4}))?\b",
            ),
            "mm_dd": re.compile(r"(\d{1,2})/(\d{1,2})"),
            "mm_dd_yyyy": re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
            "yyyy_mm_dd": re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
            "every_n_days": re.compile(r"^every (\d+ )?days?$", re.IGNORECASE),
            "every_n_weeks": re.compile(r"^every (\d+ )?weeks?$", re.IGNORECASE),
            "every_n_months": re.compile(r"^every (\d+ )?months?$", re.IGNORECASE),
            "every_n_dows": re.compile(
                r"^every (\d+) (monday|mon|tuesday|tue|wednesday"
                r"|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun)s?$",
                re.IGNORECASE,
            ),
        }

        # common replacements
        input_str = input_str.replace("every week", "every sunday")
        input_str = input_str.strip()

        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # handle edge case where time between midnight and 4am
        if now.hour < 4:
            start_date -= timedelta(days=1)

        key: ReminderKeyType | None = None
        value = ""
        frequency = None
        delete = True

        # parse input_str
        if "every" not in input_str:
            # relative
            if match := regex_patterns["relative"].search(input_str):
                number = int(match.group(1))
                unit = match.group(2)
                delta = {
                    "day": relativedelta(days=number),
                    "week": relativedelta(weeks=number),
                    "month": relativedelta(months=number),
                    "year": relativedelta(years=number),
                }[unit]
                future_date = start_date + delta
                if future_date <= start_date:
                    raise ValueError(
                        (f"{future_date.strftime('%Y-%m-%d')}" " is in the past.")
                    )
                key = ReminderKeyType.DATE
                value = future_date.strftime("%Y-%m-%d")

            # mm/dd, mm/dd/yyyy
            elif match := regex_patterns["mm_dd"].match(input_str) or regex_patterns[
                "mm_dd_yyyy"
            ].match(input_str):
                month, day = int(match.group(1)), int(match.group(2))
                year = int(match.group(3)) if match.lastindex == 3 else start_date.year
                proposed_date = datetime(year, month, day)
                key, value = set_date_key_value(proposed_date, value, key)

            # yyyy-mm-dd
            elif match := regex_patterns["yyyy_mm_dd"].match(input_str):
                year, month, day = (
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                )
                proposed_date = datetime(year, month, day)
                key, value = set_date_key_value(proposed_date, value, key)

            # day of month
            elif match := regex_patterns["day_of_month"].match(input_str):
                key = ReminderKeyType.DAY_OF_MONTH
                value = match.group(1)

            # Month + day (e.g. april 21, April 21st, apr 21) — before weekday substring
            # checks so month names like "may" / "mar" are not confused with DOW tokens.
            elif match := regex_patterns["specific_date"].search(input_str):
                month_word = match.group(1).lower().rstrip(".")
                month_num = _MONTH_NAME_TO_NUM.get(month_word)
                if month_num is None:
                    self.cabinet.log(
                        f"Unrecognized month in date: {month_word!r}",
                        level="warn",
                        is_quiet=True,
                    )
                    raise ValueError("Sorry, I didn't understand that.")
                day = int(match.group(2))
                year = (
                    int(match.group(3))
                    if match.group(3)
                    else start_date.year
                )
                try:
                    date_formatted = datetime(year, month_num, day)
                except ValueError as exc:
                    raise ValueError("Sorry, I didn't understand that.") from exc
                key, value = set_date_key_value(date_formatted, value, key)

            # specific weekday (word-boundary match; avoid "mon" inside "months")
            elif weekday_token := _match_weekday_token(input_str, weekdays):
                next_weekday = start_date + relativedelta(
                    days=1, weekday=weekdays[weekday_token]
                )
                key = ReminderKeyType.DATE
                value = next_weekday.strftime("%Y-%m-%d")

            # tomorrow
            elif input_str == "tomorrow":
                key = ReminderKeyType.DATE
                start_date += relativedelta(days=1)
                delete = True
                value = start_date.strftime("%Y-%m-%d")

            # now
            elif input_str == "now":
                key = ReminderKeyType.NOW

            # later
            elif input_str == "later":
                key = ReminderKeyType.LATER
                delete = False
        else:
            delete = False
            # Helper: Map full and abbreviated weekday names to ReminderKeyType
            weekday_to_keytype = {
                "monday": ReminderKeyType.MONDAY,
                "mon": ReminderKeyType.MONDAY,
                "tuesday": ReminderKeyType.TUESDAY,
                "tue": ReminderKeyType.TUESDAY,
                "wednesday": ReminderKeyType.WEDNESDAY,
                "wed": ReminderKeyType.WEDNESDAY,
                "thursday": ReminderKeyType.THURSDAY,
                "thu": ReminderKeyType.THURSDAY,
                "friday": ReminderKeyType.FRIDAY,
                "fri": ReminderKeyType.FRIDAY,
                "saturday": ReminderKeyType.SATURDAY,
                "sat": ReminderKeyType.SATURDAY,
                "sunday": ReminderKeyType.SUNDAY,
                "sun": ReminderKeyType.SUNDAY,
            }

            # every n days
            if match := regex_patterns["every_n_days"].match(input_str):
                key = ReminderKeyType.DAY
                frequency = int(match.group(1) or 1)

            # every n weeks
            elif match := regex_patterns["every_n_weeks"].match(input_str):
                key = ReminderKeyType.WEEK
                frequency = int(match.group(1) or 1)

            # every n months
            elif match := regex_patterns["every_n_months"].match(input_str):
                key = ReminderKeyType.MONTH
                frequency = int(match.group(1) or 1)

            # every n {dow}s (e.g., 'every 3 mondays')
            elif match := regex_patterns["every_n_dows"].match(input_str):
                dow = match.group(2).lower()
                if dow in weekdays:
                    key = weekday_to_keytype[dow]
                    value = dow
                    frequency = int(match.group(1))

            # every {dow} (e.g., 'every friday') — word-boundary match
            elif weekday_token := _match_weekday_token(input_str, weekdays):
                key = weekday_to_keytype[weekday_token]
                value = weekday_token
                frequency = 1

            # every n weeks (explicit "every N weeks" already handled above;
            # keep for "every 2 week" singular edge via every_weeks pattern)
            elif match := regex_patterns["every_weeks"].match(input_str):
                key = ReminderKeyType.WEEK
                frequency = int(match.group(1))

        if key is None:
            self.cabinet.log(
                f"Could not parse date: {input_str}", level="warn", is_quiet=True
            )
            raise ValueError("Sorry, I didn't understand that.")

        return Reminder(
            key=key,
            value=value,
            frequency=frequency,
            starts_on="",
            delete=delete,
            command="",
            title="",
            notes="",
            index=0,
            offset=0,
            cabinet=self.cabinet,
            mail=self.mail,
            path_remind_file=self.manager.remind_path_file or "",
            email=None,
        )

    def wizard_manual_reminder(
        self,
        title: str | None = None,
        when: str | None = None,
        notes: str | None = None,
        starts_on: str | None = None,
        save: bool = False,
        tags: List[str] | None = None,
    ) -> Reminder:
        """
        Guides the user through the process of creating a new manual reminder
        by collecting necessary information
        through interactive prompts.

        Parameters:
            - title (str, optional): the reminder's title (email subject)
            - when (str, optional): when you should be reminded, in natural language
            - notes (str, optional): notes (sent in the email body; HTML supported)
            - starts_on (str, optional): when the reminder should start
            - save (bool, optional): whether to save without confirmation
            - tags (List[str], optional): list of tags for the reminder
        Returns:
            - Reminder: An instance of the Reminder class with
            properties populated based on user input.
        """

        def _format_input(text: str) -> str:
            return input(f"{text}?\n")

        title = title or _format_input("What's the reminder").strip()
        reminder_date_success: bool = False
        reminder_date: str = ""

        while not reminder_date_success:
            try:
                if save and not when:
                    reminder_date = "now"
                else:
                    reminder_date = (
                        when or _format_input("When do you want to be reminded").strip()
                    )

                reminder: Reminder = self.interpret_reminder_date(reminder_date)
                reminder.title = title
                reminder.notes = notes or ""
                reminder.starts_on = starts_on
                reminder.tags = tags or []
                reminder_date_success = True
            except ValueError as e:
                print(e)
                when = None

        # display confirmation form if not `--save`
        if not save:
            try:
                ReminderConfirmation(reminder).run()
            except KeyboardInterrupt:
                sys.exit(0)
        else:
            print_formatted_text(HTML("<ansigreen><b>Done.</b></ansigreen>"))

        # 'canceled' placed by ReminderConfirmation if canceled
        if reminder.canceled:
            return reminder

        if reminder.key == ReminderKeyType.NOW:
            reminder.send_email()
        else:
            reminder.write_to_file()

        return reminder
