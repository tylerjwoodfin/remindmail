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

    Attributes:
        db_value (str): The database value associated with the enum member.
        label (str): The human-readable label for the enum member.
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
        """
        Retrieves the enum member associated with a specific database value.

        Args:
            db_value (str): The database value to match against enum members.

        Raises:
            ValueError: If `db_value` does not correspond to any enum members.

        Returns:
            ReminderKeyType: The enum member matching the given database value.
        """
        for member in cls:
            if member.db_value == db_value:
                return member
        raise ValueError(f"{db_value} is not a valid db_value of ReminderKeyType")

    def __init__(self, db_value, label):
        """
        Initialize a new instance of the ReminderKeyType enum.

        Args:
            db_value (str): The database value of the enum member.
            label (str): The label of the enum member.
        """
        self.db_value: str = db_value
        self.label: str = label

class Reminder:
    """
    Represents a reminder with various attributes defining its schedule and actions.

    Attributes:
        key (ReminderKeyType).
        - This is the type of reminder, such as on a certain day, date, or month.
        value (Optional[str]): Specific value, depending on the `key`. 
            - if key is "date", expect YYYY-MM-DD str
            - if key is "dow", expect "sun" - "sat"
            - if key is "dom", expect 1-30 as string
            - otherwise, value is ignored
        frequency (Optional[int]): Defines the frequency or interval for the reminder.
        offset (int): Adjusts the starting point of the reminder.
        modifiers (str): Contains actions for the reminder, such as delete ('d') or command ('c').
        title (str): The title or main content of the reminder.
        notes (str): Additional notes associated with the reminder.
        cabinet (Cabinet): instance of Cabinet, a file management tool
        mail (Mail): The instance in which to send reminders as emails
        path_remind_file: The path from ReminderManager in which to access remind.md
    """
    def __init__(self,
                 key,
                 value: Optional[str],
                 frequency: Optional[int],
                 offset: int,
                 modifiers: str,
                 title: str,
                 notes: Optional[str],
                 cabinet: Cabinet,
                 mail: Mail,
                 path_remind_file: str | None):
        self.key = key
        self.value: Optional[str] = value
        self.frequency: int = frequency or 0
        self.offset: int = offset
        self.modifiers: str = modifiers
        self.title: str = title
        self.notes: Optional[str] = notes
        self.should_send_today: Optional[bool] = False
        self.cabinet: Cabinet = cabinet
        self.mail: Mail = mail
        self.path_remind_file: str | None = path_remind_file

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

                # if the reminder is scheduled in the past as YYYY-MM-DD
                # and it didn't send, then for the purposes of `generate()`,
                # set the date to today so it can send, then add a note about it.
                if reminder_date < today:
                    self.notes = f"This was scheduled to send on {reminder_date}."
                    reminder_date = datetime.now().date()
            return reminder_date == today

        # Handle day of the week reminders
        elif self.key == ReminderKeyType.DAY_OF_WEEK and self.value:
            dow_mapping = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}

            # default to non-existant day
            target_dow = dow_mapping.get(self.value.lower(), 7)

            # handle day not found
            if target_dow == 7:
                self.cabinet.log(
                    f"Could not map {self.value} to a day of the week. Use [sun] to [sat].",
                    level="warn"
                )

            if today.weekday() != target_dow:
                return False

            # calculate the number of days since the epoch start
            epoch_start = date(1970, 1, 1)
            days_since_epoch = (today - epoch_start).days

            # find the first occurrence of the target day of the week from epoch
            days_to_target_dow = (target_dow - epoch_start.weekday()) % 7
            first_target_dow = epoch_start + timedelta(days=days_to_target_dow)

            # calculate weeks since the first occurrence of the target day
            weeks_since_first_target = (today - first_target_dow).days // 7

            # adjust for offset and check against frequency
            adjusted_weeks = weeks_since_first_target - self.offset
            return adjusted_weeks % self.frequency == 0

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

            if day_of_month > 31:
                self.cabinet.log(
                    f"{day_of_month} in {self.title}: no month has more than 31 days",
                    level="error")
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

        self.mail.send(email_title, self.notes or "", is_quiet=is_quiet)

    def write_to_file(self, is_quiet: bool = True) -> None:
        """
        Writes the reminder to remind.md.

        Args:
            is_quiet (bool, optional): whether to print cabinet log.
            Defaults to True.
        """

        def format_reminder():
            """
            Formats the reminder for writing to file based on its attributes.
            """
            base_format = f"\n[{self.key.db_value}"
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

        path_remind_file = self.path_remind_file or \
            self.cabinet.get('path', 'remindmail', 'file') or ""
        path_remind_folder = path_remind_file.replace("/remind.md", "")

        self.cabinet.write_file('remind.md',
                                path_remind_folder,
                                reminder_format,
                                append=True,
                                is_quiet=is_quiet)
