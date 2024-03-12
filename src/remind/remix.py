"""
The main class
"""
from datetime import datetime
from typing import List, Optional, Dict
import re

class Reminder:
    """
    Represents a reminder with various attributes defining its schedule and actions.

    Attributes:
        reminder_type (str): Type of reminder (e.g., 'd', 'w', 'm', 'dow', 'dom', 'later').
        date (Optional[str]): Specific date for one-time reminders in YYYY-MM-DD or MM-DD.
        cycle (Optional[int]): Defines the cycle or interval for the reminder.
        offset (int): Adjusts the starting point of the reminder.
        modifiers (str): Contains actions for the reminder, such as delete ('d') or command ('c').
        title (str): The title or main content of the reminder.
        notes (str): Additional notes associated with the reminder.
    """
    def __init__(self, reminder_type: str, date: Optional[str], cycle: Optional[int],
                 offset: int, modifiers: str, title: str, notes: Optional[str]):
        self.reminder_type: str = reminder_type
        self.date: Optional[str] = date
        self.cycle: Optional[int] = cycle
        self.offset: int = offset
        self.modifiers: str = modifiers
        self.title: str = title
        self.notes: Optional[str] = notes

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

def parse_reminders_file(filename: str) -> List[Reminder]:
    """
    Parses a markdown file containing reminders into an array of Reminder objects.

    Each line of the file is expected to define a reminder or 
    a note associated with the preceding reminder.
    Comments and empty lines are ignored. The reminders are parsed based on predefined formats and
    accumulated into Reminder objects, which are then returned in a list.

    Args:
        filename (str): The path to the markdown file containing the reminders.

    Returns:
        List[Reminder]: A list of Reminder objects parsed from the file.
    """
    reminders: List[Reminder] = []
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
            if line.startswith("#") or line.startswith("<!--") or line.startswith("%%") or not line:
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
                    date: Optional[str] = None
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
                        date = "later"
                    else:
                        date = details[0]  # for specific dates

                    reminders.append(Reminder(reminder_type, date, cycle, offset,
                                              modifiers, title.strip(), ''))
            else:
                current_notes.append(line)

        if current_notes:  # catch notes for the last reminder
            reminders[-1].notes = "\n".join(current_notes)

    return reminders

def should_send_today(reminder: Reminder) -> bool:
    """
    Determines whether a given Reminder should send today based on its scheduling details.

    Args:
        reminder (Reminder): The reminder to check, containing its schedule and any conditions.

    Returns:
        bool: True if the reminder is scheduled to send today, False otherwise.
    """
    today = datetime.now()

    if isinstance(reminder.reminder_type, int) and reminder.reminder_type in range(7):
        # For weekly reminders set on a specific day of the week
        if today.weekday() == reminder.reminder_type:
            if reminder.cycle is None or reminder.cycle == 1:
                return True
            else:
                # Handle reminders that occur every 'n' weeks with an optional offset
                start_date = datetime(1970, 1, 1)
                weeks_since_start = (today - start_date).days // 7
                return (weeks_since_start + reminder.offset) % reminder.cycle == 0
        return False
    elif reminder.reminder_type == "d":
        # Daily reminders, possibly with a cycle (every 'n' days)
        if reminder.cycle is None or reminder.cycle == 1:
            return True
        else:
            if reminder.date:
                start_date = datetime.strptime(reminder.date, '%Y-%m-%d')
                days_since_start = (today - start_date).days
                return (days_since_start + reminder.offset) % reminder.cycle == 0
            else:
                return True
    elif reminder.reminder_type == "m":
        # Monthly reminders, occurring on the first of each month
        if reminder.cycle is None or reminder.cycle == 1:
            return today.day == 1
        else:
            return False  # Monthly cycle handling could be expanded based on specific requirements
    elif reminder.date:
        # Specific date reminders
        try:
            specific_date = datetime.strptime(reminder.date, '%Y-%m-%d')
            return today.date() == specific_date.date()
        except ValueError:
            # Handle MM-DD format or other date format mismatches
            return False
    elif reminder.reminder_type == "later":
        # 'later' type reminders do not have a specific send date
        return False

    # Default case if none of the conditions match
    return False

# Example usage
parsed_reminders = parse_reminders_file('remix.md')
for r in parsed_reminders:
    if should_send_today(r):
        print(r)
