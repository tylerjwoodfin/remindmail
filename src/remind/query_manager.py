"""
handles reminder requests
"""

from remind.reminder import Reminder
from remind.reminder_manager import ReminderManager
from cabinet import Cabinet, Mail

class QueryManager:
    """
    handles reminder requests
    """

    def __init__(self, manager: ReminderManager) -> None:
        self.cabinet: Cabinet = manager.cabinet
        self.mail: Mail = manager.mail
        return

    def write_reminder_to_file(self, reminder: Reminder) -> None:
        """
        writes a reminder to remind.md
        """
        print("Not yet Implemented\n")
        print(reminder)

    def wizard_manual_reminder(self) -> Reminder:
        """
        Guides the user through the process of creating a new manual reminder
        by collecting necessary information
        through interactive prompts.

        Returns:
            Reminder: An instance of the Reminder class with
            properties populated based on user input.
        """

        def _format_input(text: str) -> str:
            return input(f"{text}?\n")

        title = _format_input("What's the reminder").strip()
        reminder_date = _format_input(
            "When do you want to be reminded").strip() or None
        reminder_type = _format_input("reminder type (d, w, m, dow, dom, later)").strip()
        cycle_input = _format_input("cycle or interval (number of days, optional)").strip()
        cycle = int(cycle_input) if cycle_input.isdigit() else None
        offset = int(_format_input("offset (default is 0)") or 0)
        modifiers = _format_input("any modifiers (e.g., 'd' for delete, 'c' for command)").strip()
        notes = _format_input("any notes for the reminder (optional)").strip() or None

        reminder = Reminder(reminder_type=reminder_type,
                        reminder_date=reminder_date,
                        cycle=cycle,
                        offset=offset,
                        modifiers=modifiers,
                        title=title,
                        notes=notes,
                        cabinet=self.cabinet,
                        mail=self.mail)

        self.write_reminder_to_file(reminder)

        return reminder
