"""
The main class
"""
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
from cabinet import Cabinet, Mail

class ReminderKeyType(Enum):
    """
    Enum for `Reminder.key` with database value and label.
    """
    DATE = ("date", "Date")
    DAY = ("d", "Day")
    WEEK = ("w", "Week")
    MONTH = ("m", "Month")
    DAY_OF_WEEK = ("dow", "Day of Week")
    DAY_OF_MONTH = ("dom", "Day of Month")
    LATER = ("later", "Later")

    def __init__(self, db_value, label):
        self.db_value: str = db_value  # Assign to custom attribute
        self.label: str = label  # Assign to custom attribute

class Reminder:
    """
    Represents a reminder with various attributes defining its schedule and actions.

    Attributes:
        key (KeyType). This is the type of reminder, such as on a certain day, date, or month.
        value (Optional[str]): Specific value, depending on the `key`. 
            - if key is "date", expect YYYY-MM-DD str
            - if key is "dow", expect "sun" - "sat"
            - if key is "dom", expect 1-30 as string
            - otherwise, value is ignored
        cycle (Optional[int]): Defines the cycle or interval for the reminder.
        offset (int): Adjusts the starting point of the reminder.
        modifiers (str): Contains actions for the reminder, such as delete ('d') or command ('c').
        title (str): The title or main content of the reminder.
        notes (str): Additional notes associated with the reminder.
    """
    def __init__(self,
                 key: ReminderKeyType,
                 value: Optional[str],
                 frequency: Optional[int],
                 offset: int,
                 modifiers: str,
                 title: str,
                 notes: Optional[str],
                 cabinet: Cabinet,
                 mail: Mail):
        self.key: ReminderKeyType = key
        self.value: Optional[str] = value
        self.frequency: Optional[int] = frequency
        self.offset: int = offset
        self.modifiers: str = modifiers
        self.title: str = title
        self.notes: Optional[str] = notes
        self.should_send_today: Optional[bool] = False
        self.cabinet: Cabinet = cabinet
        self.mail: Mail = mail

    def __repr__(self) -> str:
        return (
            f"Reminder(key={self.key}, "
            f"value={self.value}, "
            f"frequency={self.frequency}, "
            f"offset={self.offset}, "
            f"modifiers='{self.modifiers}', "
            f"title='{self.title}', "
            f"notes='{self.notes}')"
            "\n"
        )

    def get_should_send_today(self, date_override: datetime.date = None) -> bool:
        """
        Determines whether the reminder should be sent today based on its scheduling configuration.

        This method evaluates the reminder's key, value, frequency, and offset to calculate whether
        the current day matches the scheduled day for the reminder to be sent. It supports various
        reminder keys, including specific dates, days of the week, daily intervals, weekly
        intervals, monthly intervals, and specific days of the month. The calculation considers the
        current date, or an optional override date, to determine if the conditions for sending
        the reminder are met today.

        Args:
            date_override (datetime.date, optional): A specific date to evaluate the reminder
            against, instead of the current date.

        Returns:
            bool:   True if the reminder should be sent today based on its scheduling details
                    False otherwise.
        """
        today = date_override or datetime.now().date()
        # Handle date-specific reminders
        if self.key == 'date' and self.value:
            return datetime.strptime(self.value, '%Y-%m-%d').date() == today

        # Handle day of the week reminders
        elif self.key == 'dow' and self.value:
            dow_mapping = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
            target_dow = dow_mapping.get(self.value.lower())
            if today.weekday() == target_dow:
                if self.frequency:
                    start_date = today - timedelta(days=today.weekday()) + timedelta(
                        days=target_dow, weeks=-self.offset)
                    weeks_diff = (today - start_date).days // 7
                    return weeks_diff % self.frequency == 0
                return True

        # Handle daily reminders with optional frequency
        elif self.key == 'd':
            if self.frequency:
                start_date = today - timedelta(days=self.offset)
                days_diff = (today - start_date).days
                return days_diff % self.frequency == 0
            return True

        # Handle weekly reminders
        elif self.key == 'w':
            if self.frequency:
                start_date = today - timedelta(weeks=self.offset)
                weeks_diff = (today - start_date).days // 7
                return weeks_diff % self.frequency == 0
            return True

        # Handle monthly reminders using standard datetime calculations
        elif self.key == 'm' and self.frequency:
            try:
                months_since_start = today.month + (today.year - 1970) * 12 - self.offset
                return months_since_start % self.frequency == 0
            except ValueError:
                return False

        # Handle day of the month reminders
        elif self.key == 'dom' and self.value:
            day_of_month = int(self.value)
            return today.day == day_of_month

        return False

    def send_email(self, is_quiet: bool = False):
        """
        Sends the reminder as an email using Cabinet's `Mail()` module
        """

        email_icons = ""

        if self.notes:
            email_icons += "🗒️"

        # add more icons in future iterations

        email_icons = f"{email_icons} " if email_icons else email_icons
        email_title = f"Reminder {email_icons}- {self.title}"

        # self.mail.send(email_title, self.notes, is_quiet=is_quiet)
        self.cabinet.log(f"DEBUG: pretending to send {email_title}, {self.notes}, {is_quiet}")
