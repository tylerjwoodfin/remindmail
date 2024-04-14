"""
The main class
"""
from datetime import datetime, date, timedelta
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
    NOW = ("now", "Now")

    @classmethod
    def from_db_value(cls, db_value):
        """docstring

        Args:
            db_value (_type_): _description_

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """
        for member in cls:
            if member.db_value == db_value:
                return member
        raise ValueError(f"{db_value} is not a valid db_value of ReminderKeyType")

    def __init__(self, db_value, label):
        self.db_value: str = db_value
        self.label: str = label

class Reminder:
    """
    Represents a reminder with various attributes defining its schedule and actions.

    Attributes:
        key (ReminderKeyType).
        - This is the type of reminder, such as on a certain day, date, or month.
        - value (Optional[str]): Specific value, depending on the `key`. 
            - if key is "date", expect YYYY-MM-DD str
            - if key is "dow", expect "sun" - "sat"
            - if key is "dom", expect 1-30 as string
            - otherwise, value is ignored
        frequency (Optional[int]): Defines the frequency or interval for the reminder.
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
        self.frequency: int = frequency or 0
        self.offset: int = offset
        self.modifiers: str = modifiers
        self.title: str = title
        self.notes: Optional[str] = notes
        self.should_send_today: Optional[bool] = False
        self.cabinet: Cabinet = cabinet
        self.mail: Mail = mail

    def __repr__(self) -> str:
        return (
            f"Reminder(key={self.key.db_value}, "
            f"value={self.value}, "
            f"frequency={self.frequency}, "
            f"offset={self.offset}, "
            f"modifiers='{self.modifiers}', "
            f"title='{self.title}', "
            f"notes='{self.notes}')"
            "\n"
        )

    def get_should_send_today(self, date_override: date | None = None) -> bool:
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
        if self.key == ReminderKeyType.DATE and self.value:
            if len(self.value) == 5:  # MM-DD format
                reminder_date = datetime.strptime(f"{today.year}-{self.value}", '%Y-%m-%d').date()
                if reminder_date < today:
                    reminder_date = datetime.strptime(
                        f"{today.year + 1}-{self.value}", '%Y-%m-%d').date()
            else:  # YYYY-MM-DD format
                reminder_date = datetime.strptime(self.value, '%Y-%m-%d').date()
            return reminder_date == today

        # Handle day of the week reminders
        elif self.key == ReminderKeyType.DAY_OF_WEEK and self.value:
            dow_mapping = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
            target_dow = dow_mapping.get(self.value.lower(), 6)
            if today.weekday() == target_dow:
                start_date = today - timedelta(days=today.weekday()) \
                    + timedelta(days=target_dow, weeks=-self.offset)
                weeks_diff = (today - start_date).days // 7
                return weeks_diff % self.frequency == 0 if self.frequency > 0 else True

        # Handle every n days
        elif self.key == ReminderKeyType.DAY:
            if self.frequency > 0:
                epoch_start = date(1970, 1, 1)
                days_since_epoch = (today - epoch_start).days
                adjusted_days = days_since_epoch - self.offset
                return adjusted_days % self.frequency == 0
            return True

        # Handle weekly reminders
        elif self.key == ReminderKeyType.WEEK:
            if self.frequency > 0:
                start_date = today - timedelta(weeks=self.offset)
                weeks_diff = (today - start_date).days // 7
                return weeks_diff % self.frequency == 0 and today.weekday() == 6
            return True

        # Handle monthly reminders
        elif self.key == ReminderKeyType.MONTH and self.frequency:
            months_since_start = today.month + (today.year - 1970) * 12 - self.offset
            return today.day == 1 and months_since_start % self.frequency == 0

        # Handle day of the month reminders
        elif self.key == ReminderKeyType.DAY_OF_MONTH and self.value:
            day_of_month = int(self.value)
            return today.day == day_of_month

        return False


    def send_email(self, is_quiet: bool = False) -> None:
        """
        Sends the reminder as an email using Cabinet's `Mail()` module

        Args:
            is_quiet (bool, optional): whether to print cabinet log.
            Defaults to False.
        """

        email_icons = ""

        if self.notes:
            email_icons += "🗒️"

        # add more icons in future iterations

        email_icons = f"{email_icons} " if email_icons else email_icons
        email_title = f"Reminder {email_icons}- {self.title}"

        # self.mail.send(email_title, self.notes, is_quiet=is_quiet)
        self.cabinet.log(f"DEBUG: pretending to send {email_title}, {self.notes}, {is_quiet}")

    def write_to_file(self, is_quiet: bool = False) -> None:
        """
        Writes the reminder to remind.md.

        Args:
            is_quiet (bool, optional): whether to print cabinet log.
            Defaults to False.
        """

        def format_reminder():
            """
            Formats the reminder for writing to file based on its attributes.
            """
            base_format = f"[{self.key.db_value}"
            if self.key == ReminderKeyType.DATE:
                base_format = "["

            if self.key not in [ReminderKeyType.DATE,
                                ReminderKeyType.DAY_OF_WEEK,
                                ReminderKeyType.DAY_OF_MONTH]:
                self.value = ""

            if self.value:
                base_format += f",{self.value}"
            if self.frequency:
                base_format += f",{self.frequency}"
            if self.offset:
                base_format += f",{self.offset}"

            if self.key == ReminderKeyType.LATER:
                base_format = "[later"
                self.modifiers = ""

            base_format += f"]{self.modifiers} {self.title}\n"


            if self.notes:
                base_format += f"{self.notes}\n"

            base_format = base_format.replace("[,", "[")

            return base_format

        reminder_format = format_reminder()

        # with open(file_path, 'a') as file:
        #     file.write(reminder_format)

        print("WRITING")
        print(reminder_format)
