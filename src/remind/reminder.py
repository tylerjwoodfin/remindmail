"""
The main class
"""
import calendar
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import subprocess
from typing import Optional, List
from enum import Enum
from cabinet import Cabinet, Mail
import yaml
from remind.error_handler import ErrorHandler
class ReminderKeyType(Enum):
    DATE = ("date", "Date")
    DAY = ("d", "Day")
    WEEK = ("w", "Week")
    MONTH = ("m", "Month")
    DAY_OF_MONTH = ("dom", "Day of Month")
    SUNDAY = ("sun", "Sunday")
    MONDAY = ("mon", "Monday")
    TUESDAY = ("tue", "Tuesday")
    WEDNESDAY = ("wed", "Wednesday")
    THURSDAY = ("thu", "Thursday")
    FRIDAY = ("fri", "Friday")
    SATURDAY = ("sat", "Saturday")
    LATER = ("later", "Later")
    NOW = ("now", "Now")

    @classmethod
    def from_db_value(cls, db_value):
        for member in cls:
            if member.db_value == db_value:
                return member
        raise ValueError(f"{db_value} is not a valid db_value of ReminderKeyType")

    @classmethod
    def from_csv_values(cls, csv_string):
        """
        Parses a comma-separated string of db_values and returns a list of matching enum members.

        Args:
            csv_string (str): Comma-separated string of db_values like 'mon,wed,fri'

        Returns:
            List[ReminderKeyType]: List of corresponding enum members
        """
        values = [v.strip() for v in csv_string.split(",")]
        return [cls.from_db_value(v) for v in values]

    @classmethod
    def is_key_day_of_week(cls, key):
        """
        Determines if the reminder key is a day of the week.

        Args:
            key (ReminderKeyType): The reminder key to check.

        Returns:
            bool: True if the key is a day of the week, False otherwise.
        """
        return key in [
            cls.SUNDAY,
            cls.MONDAY,
            cls.TUESDAY,
            cls.WEDNESDAY,
            cls.THURSDAY,
            cls.FRIDAY,
            cls.SATURDAY
        ]

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
        delete (bool): Whether to delete the reminder.
        command (str): If set, runs the command and outputs the results to the body of the email.
        title (str): The title or main content of the reminder.
        notes (str): Additional notes associated with the reminder.
        tags (List[str]): Optional list of tags associated with the reminder.
        index (int): The index of the actual line in which this reminder starts in remindmail.yml
        cabinet (Cabinet): instance of Cabinet, a file management tool
        mail (Mail): The instance in which to send reminders as emails
        path_remind_file: The path from ReminderManager in which to access remindmail.yml
    """
    def __init__(self,
                 key: ReminderKeyType,
                 title: str,
                 value: Optional[date|str],
                 frequency: Optional[int],
                 starts_on: Optional[str],
                 offset: int,
                 delete: bool,
                 command: str,
                 notes: str,
                 index: int,
                 cabinet: Cabinet,
                 mail: Mail,
                 path_remind_file: str,
                 tags: Optional[List[str]] = None) -> None:
        self.key = key
        self.value = value
        self.frequency = frequency
        self.starts_on = starts_on
        self.offset = offset
        self.delete = delete
        self.command = command
        self.title = title
        self.notes = notes
        self.index = index
        self.cabinet = cabinet
        self.mail = mail
        self.path_remind_file = path_remind_file
        self.tags = tags or []
        self.should_send_today = False
        self.canceled = False # set to True if user cancels reminder in confirmation
        self.error_handler = ErrorHandler()
        
        if self.path_remind_file == '':
            raise ValueError("path_remind_file cannot be empty")

    def __repr__(self) -> str:
        return (
            f"Reminder(key={self.key.db_value},\n"
            f"title='{self.title}',\n"
            f"value={self.value},\n"
            f"frequency={self.frequency},\n"
            f"starts_on={self.starts_on},\n"
            f"offset={self.offset},\n"
            f"delete={self.delete},\n"
            f"command='{self.command}',\n"
            f"notes='{self.notes}',\n"
            f"tags={self.tags},\n"
            f"canceled={self.canceled},\n"
            f"should_send_today={self.should_send_today})"
        )
    
    def __str__(self):
        return self.__repr__()

    def get_should_send_today(self, target_date: date | None = None, hide_past_warning: bool = False) -> bool:
        """
        Determines if the reminder should be sent today.

        Args:
            target_date (date, optional): The date to check against. If None, uses today's date.

        Returns:
            bool: True if the reminder should be sent today, False otherwise.
        """
        if target_date is None:
            target_date = date.today()

        # Handle different reminder types
        if self.key == ReminderKeyType.DATE:
            # Validate that value is not empty or None
            if not self.value or str(self.value).strip() == '':
                return False
                
            # Parse the date string (YYYY-MM-DD or MM-DD)
            date_parts = str(self.value).split('-')
            
            # Validate that we have valid date parts
            if len(date_parts) != 2 and len(date_parts) != 3:
                return False
                
            # Check for empty parts
            if any(not part.strip() for part in date_parts):
                return False
                
            try:
                if len(date_parts) == 2:  # MM-DD format
                    month, day = map(int, date_parts)
                    year = target_date.year
                    # If the date has already passed this year, use next year
                    if (month, day) < (target_date.month, target_date.day):
                        year += 1
                else:  # YYYY-MM-DD format
                    year, month, day = map(int, date_parts)
            except ValueError:
                # If we can't parse the date parts as integers, return False
                return False

            # if date is in the past and target date is today, send it today
            if (year, month, day) < (target_date.year, target_date.month, target_date.day) \
                and not self.canceled and not hide_past_warning:
                self.notes += f"Warning: Reminder was scheduled for {self.value}."
                return True

            return (target_date.year, target_date.month, target_date.day) == (year, month, day)

        elif self.key == ReminderKeyType.DAY_OF_MONTH:
            if not self.value or not str(self.value).isdigit():
                raise ValueError("Reminder day of month cannot be empty and must be an integer for day of month reminders.")
            return target_date.day == self.value

        elif self.key in [ReminderKeyType.MONDAY, ReminderKeyType.TUESDAY,
                         ReminderKeyType.WEDNESDAY, ReminderKeyType.THURSDAY,
                         ReminderKeyType.FRIDAY, ReminderKeyType.SATURDAY,
                         ReminderKeyType.SUNDAY]:
            # Get the weekday number (0-6, Monday-Sunday)
            target_weekday = target_date.weekday()

            reminder_weekday_str = self.key.label  # e.g., "Sunday"
            reminder_weekday_int = list(calendar.day_name).index(reminder_weekday_str)

            if target_weekday != reminder_weekday_int:
                return False

            # If frequency is set, check if it's the right week
            if self.frequency and self.frequency > 1:
                # Calculate weeks since epoch
                epoch = date(1970, 1, 1)
                days_since_epoch = (target_date - epoch).days
                weeks_since_epoch = days_since_epoch // 7

                # Apply offset
                weeks_since_epoch -= self.offset

                # Check if it's the right week
                return weeks_since_epoch % self.frequency == 0

            return True

        elif self.key == ReminderKeyType.DAY:
            if not self.frequency:
                return True

            # Calculate days since epoch
            epoch = date(1970, 1, 1)
            days_since_epoch = (target_date - epoch).days

            # Apply offset
            days_since_epoch -= self.offset

            # Check if it's the right day
            return days_since_epoch % self.frequency == 0

        elif self.key == ReminderKeyType.WEEK:
            if not self.frequency:
                return True

            # Calculate weeks since epoch
            epoch = date(1970, 1, 1)
            days_since_epoch = (target_date - epoch).days
            weeks_since_epoch = days_since_epoch // 7

            # Apply offset
            weeks_since_epoch -= self.offset

            # Check if it's the right week
            return weeks_since_epoch % self.frequency == 0

        elif self.key == ReminderKeyType.MONTH:
            if not self.frequency:
                # return if first of the month
                return target_date.day == 1

            # Calculate months since epoch
            epoch = date(1970, 1, 1)
            months_since_epoch = (target_date.year - epoch.year) * 12 + \
                               (target_date.month - epoch.month)

            # Apply offset
            months_since_epoch -= self.offset

            # Check if it's the right month
            return months_since_epoch % self.frequency == 0 and target_date.day == 1

        elif self.key == ReminderKeyType.LATER:
            return False

        elif self.key == ReminderKeyType.NOW:
            return True

        return False

    def send(self, is_quiet: bool = False) -> None:
        """
        Sends the reminder via email or executes it as a command.
        """

        if self.command:
            # Execute as command
            self.cabinet.log(f"Executing command: {self.command}", level="debug")
            try:
                # Add path so things like `cabinet` calls work from crontab
                home_dir = os.path.expanduser("~")
                path_local_bin = os.path.join(home_dir, ".local/bin")
                os.environ["PATH"] = f"{path_local_bin}:{os.environ['PATH']}"

                cmd_output = subprocess.check_output(
                    self.command, shell=True, universal_newlines=True
                )
                self.cabinet.log(f"Results: {cmd_output}", level="debug")

                if not self.notes:
                    self.notes = ""
                self.notes += f"<br><br>{cmd_output}"
            except subprocess.CalledProcessError as error:
                self.cabinet.log(
                    f"Command execution failed with exit code: {error.returncode}",
                    level="error",
                )
                self.cabinet.log(
                    f"Error output: {error.output}", level="error"
                )

        self.send_email(is_quiet=is_quiet)

    def send_email(self, is_quiet: bool = False) -> None:
        """
        Sends the reminder as an email using Cabinet's `Mail()` module

        Args:
            is_quiet (bool, optional): whether to print cabinet log.
            Defaults to False.
        """

        email_icons = "🗒️" if self.notes else ""
        if self.command:
            email_icons += "💻"

        email_title = f"Reminder {email_icons}- {self.title}"

        self.cabinet.logdb(self.title, collection_name="reminders")
        self.mail.send(email_title, self.notes or "", is_quiet=is_quiet)

    def write_to_file(self, is_quiet: bool = True) -> None:
        """
        Appends this reminder to `remindmail.yml` in valid YAML format.

        Args:
            is_quiet (bool, optional): Whether to print cabinet log output.
        """
        reminder_dict = {
            "name": self.title,
            "date": self.value,
        }

        # Handle reminder type
        if self.key == ReminderKeyType.LATER:
            reminder_dict["later"] = True
        elif self.key == ReminderKeyType.DATE:
            if not self.value or not self.error_handler.is_valid_date(str(self.value)):
                raise ValueError("Reminder date cannot be empty and must be a date for date reminders.")
            reminder_dict["date"] = datetime.strptime(str(self.value), '%Y-%m-%d').date()
        elif self.key == ReminderKeyType.DAY_OF_MONTH:
            if not self.value or not self.error_handler.is_valid_date(str(self.value)):
                raise ValueError("Reminder day of month cannot be empty and must be an integer for day of month reminders.")
            reminder_dict["dom"] = self.value
        elif self.key in {
            ReminderKeyType.SUNDAY, ReminderKeyType.MONDAY, ReminderKeyType.TUESDAY,
            ReminderKeyType.WEDNESDAY, ReminderKeyType.THURSDAY,
            ReminderKeyType.FRIDAY, ReminderKeyType.SATURDAY
        }:
            reminder_dict["day"] = self.key.db_value
            reminder_dict["every"] = self.frequency or 1
            del reminder_dict["date"]
        elif self.key == ReminderKeyType.WEEK:
            reminder_dict["every"] = self.frequency
            reminder_dict["unit"] = "weeks"
        elif self.key == ReminderKeyType.MONTH:
            reminder_dict["every"] = self.frequency
            reminder_dict["unit"] = "months"
        elif self.key == ReminderKeyType.DAY:
            reminder_dict["every"] = self.frequency

        # Optional fields
        if self.offset:
            reminder_dict["offset"] = self.offset
        if self.notes:
            reminder_dict["notes"] = self.notes
        if self.delete:
            reminder_dict["delete"] = True
        if self.tags:
            reminder_dict["tags"] = self.tags
        if self.command:
            reminder_dict["command"] = self.command

        # Load existing file (if any)
        path_remind_file = self.path_remind_file or \
            self.cabinet.get('path', 'remindmail', 'file') or ""
        remind_path = Path(path_remind_file)

        if remind_path.exists():
            with open(remind_path, "r") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # Append new reminder
        data.setdefault("reminders", []).append(reminder_dict)

        # Write it back
        with open(remind_path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        if not is_quiet:
            self.cabinet.log(f"Wrote reminder to {remind_path}")
