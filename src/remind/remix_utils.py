"""
Utils for groups of reminders
"""

import re
from typing import List, Optional, Dict
from . import remix

class RemindmailUtils:
    """
    Utils for groups of reminders
    """

    def parse_reminders_file(self, filename: str) -> List[remix.Reminder]:
        """
        Parses a markdown file containing reminders into an array of Reminder objects.

        Each line of the file is expected to define a reminder or 
        a note associated with the preceding reminder.
        Comments and empty lines are ignored.
        The reminders are parsed based on predefined formats and
        accumulated into Reminder objects, which are then returned in a list.

        Args:
            filename (str): The path to the markdown file containing the reminders.

        Returns:
            List[Reminder]: A list of Reminder objects parsed from the file.
        """
        reminders: List[remix.Reminder] = []
        current_notes: List[str] = []

        # Mapping from day names to their integer representation (Monday=0)
        day_to_int: Dict[str, int] = {
            "mon": 0,
            "tue": 1,
            "wed": 2,
            "thu": 3,
            "fri": 4,
            "sat": 5,
            "sun": 6
        }

        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if (line.startswith("#") or
                    line.startswith("<!--") or
                    line.startswith("%%") or
                    not line):

                    continue  # Skip comments or empty lines

                if line.startswith("["):
                    if current_notes:  # save previous reminder notes
                        reminders[-1].notes = "\n".join(current_notes)
                        current_notes = []  # reset notes for next reminder

                    pattern = r"\[(.*?)\](c?d?)\s*(.*)"
                    match = re.match(pattern, line)
                    if match:
                        details, modifiers, title = match.groups()
                        details = details.split(",")
                        reminder_type: str = details[0]
                        reminder_date: Optional[str] = None
                        cycle: Optional[int] = None
                        offset: int = 0

                        if reminder_type in ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]:
                            cycle = 1
                            if len(details) > 1:
                                cycle = int(details[1])
                            offset = int(details[2]) if len(details) > 2 else 0
                            reminder_type = day_to_int[reminder_type]  # Convert day to int
                        elif reminder_type in ["d", "w", "m", "dom"]:
                            cycle = int(details[1]) if len(details) > 1 else None
                            offset = int(details[2]) if len(details) > 2 else 0
                        elif reminder_type == "later":
                            reminder_date = "later"
                        else:
                            reminder_date = details[0]  # for specific dates

                        reminder = remix.Reminder(reminder_type, reminder_date, cycle, offset,
                                                modifiers, title.strip(), '')
                        reminder.should_send_today = reminder.get_should_send_today()
                        reminders.append(reminder)
                else:
                    current_notes.append(line)

            if current_notes:  # catch notes for the last reminder
                reminders[-1].notes = "\n".join(current_notes)

        return reminders

    def generate(self):
        """
        Generates reminders from the file.
        """

        parsed_reminders = self.parse_reminders_file('remix.md')

        for r in parsed_reminders:
            if r.should_send_today:
                print(r.title)
                if 'd' in r.modifiers:
                    print("Deleting")

                if 'c' in r.modifiers:
                    print("Executing")

                print("Sending")

    def show_week(self):
        """
        Shows upcoming reminders for the week
        """
