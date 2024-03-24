"""
The main class
"""
from datetime import datetime, date
from typing import Optional
from cabinet import Cabinet, Mail

class Reminder:
    """
    Represents a reminder with various attributes defining its schedule and actions.

    Attributes:
        reminder_type (str): Type of reminder (e.g., 'd', 'w', 'm', 'dow', 'dom', 'later').
        reminder_date (Optional[str]): Specific date for one-time reminders in YYYY-MM-DD or MM-DD.
        cycle (Optional[int]): Defines the cycle or interval for the reminder.
        offset (int): Adjusts the starting point of the reminder.
        modifiers (str): Contains actions for the reminder, such as delete ('d') or command ('c').
        title (str): The title or main content of the reminder.
        notes (str): Additional notes associated with the reminder.
    """
    def __init__(self, reminder_type: str, reminder_date: Optional[str], cycle: Optional[int],
                 offset: int, modifiers: str, title: str,
                 notes: Optional[str], cabinet: Cabinet, mail: Mail):
        self.reminder_type: str = reminder_type
        self.date: Optional[str] = reminder_date
        self.cycle: Optional[int] = cycle
        self.offset: int = offset
        self.modifiers: str = modifiers
        self.title: str = title
        self.notes: Optional[str] = notes
        self.should_send_today: Optional[bool] = False
        self.cabinet: Cabinet = cabinet
        self.mail: Mail = mail

    def __repr__(self) -> str:
        return (
            f"Reminder(type={self.reminder_type}, "
            f"date={self.date}, "
            f"cycle={self.cycle}, "
            f"offset={self.offset}, "
            f"modifiers='{self.modifiers}', "
            f"title='{self.title}', "
            f"notes='{self.notes}')"
        )

    def get_should_send_today(self, date_override: date = None) -> bool:
        """
        Determines whether a given Reminder should send today based on its scheduling details.

        Args:
            reminder (Reminder): The reminder to check, containing its schedule and any conditions.
            date_override (date): Check whether a reminder should send on another date

        Returns:
            bool: True if the reminder is scheduled to send today, False otherwise.
        """
        today = date_override or datetime.now().date()

        if isinstance(self.reminder_type, int) and self.reminder_type in range(7):
            # For weekly reminders set on a specific day of the week
            if today.weekday() == self.reminder_type:
                if self.cycle is None or self.cycle == 1:
                    return True
                else:
                    # Handle reminders that occur every 'n' weeks with an optional offset
                    start_date = datetime(1970, 1, 1)
                    weeks_since_start = (today - start_date).days // 7
                    return (weeks_since_start + self.offset) % self.cycle == 0
            return False
        if self.reminder_type == "d":
            # Daily reminders, possibly with a cycle (every 'n' days)
            if self.cycle is None or self.cycle == 1:
                return True
            else:
                # Use the provided date or Unix epoch as the start date
                unix_epoch = datetime(1970, 1, 1).date()
                if self.date:
                    start_date = datetime.strptime(self.date, '%Y-%m-%d').date()
                else:
                    start_date = unix_epoch
                days_since_start = (today - start_date).days
                # Adjust for the offset, if any
                adjusted_days = days_since_start + (self.offset if self.offset else 0)
                return adjusted_days % self.cycle == 0
        elif self.reminder_type == "m":
            # Monthly reminders, occurring on the first of each month
            if self.cycle is None or self.cycle == 1:
                return today.day == 1
            else:
                return False
        elif self.date:
            # Specific date reminders
            try:
                specific_date = datetime.strptime(self.date, '%Y-%m-%d')
                return today == specific_date.date()
            except ValueError:
                # Handle MM-DD format or other date format mismatches
                return False
        # Default case if none of the conditions match
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
