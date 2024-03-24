"""
Utils for groups of reminders
"""

import re
import os
import sys
from typing import List, Optional, Dict
from cabinet import Cabinet, Mail
from . import remix

class RemindmailUtils:
    """
    A utility class for handling reminders and email operations.
    """

    def __init__(self) -> None:

        # instance of the Cabinet class for configuration management
        self.cab = Cabinet()

        # file path for reminders
        self.path_remind_file = self.cab.get('path', 'remindmail', 'file')

        # for sending emails
        self.mail = Mail()

        # parse reminders file for later access

        # DEBUG
        # self.parsed_reminders = self.parse_reminders_file()
        self.parsed_reminders = self.parse_reminders_file('src/remind/remix.md')

    def parse_reminders_file(self, filename: str = None) -> List[remix.Reminder]:
        """
        Parses a markdown file containing reminders into an array of Reminder objects.

        Each line of the file is expected to define a reminder or 
        a note associated with the preceding reminder.
        Comments and empty lines are ignored.
        The reminders are parsed based on predefined formats and
        accumulated into Reminder objects, which are then returned in a list.
        
        After parsing Reminders into a List, delete
        reminders scheduled for today with a "d" modifier from the file.

        Args:
            filename (str, optional): The path to the markdown file containing the reminders.
                If unset, defaults to self.path_remind_file

        Returns:
            List[Reminder]: A list of Reminder objects parsed from the file.
        """

        reminders: List[remix.Reminder] = []
        current_notes: List[str] = []

        # handle filename
        if filename is None:
            filename = self.path_remind_file

            if os.path.isdir(filename):
                old_value = filename
                if filename.endswith('/'):
                    filename = filename.rstrip('/')
                new_value = f"{filename}/remind.md"
                filename = new_value
                self.cab.log(
                    "Updating path -> remindmail -> file in "
                    f"Cabinet from '{old_value}' to '{new_value}'"
                )
                self.cab.put("path", "remindmail", "file", filename)
                print(self.cab.get("path", "remindmail", "file", no_cache=True))


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

                    # skip comments or empty lines
                    continue

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

                        reminder = remix.Reminder(reminder_type,
                                                  reminder_date,
                                                  cycle,
                                                  offset,
                                                  modifiers,
                                                  title.strip(),
                                                  '',
                                                  self.cab,
                                                  self.mail)
                        reminder.should_send_today = reminder.get_should_send_today()
                        reminders.append(reminder)
                else:
                    current_notes.append(line)

            if current_notes:  # catch notes for the last reminder
                reminders[-1].notes = "\n".join(current_notes)

        return reminders

    def generate(self):
        """
        Sends or executes reminders from the file that are scheduled to send today 
        (per parse_reminders_file).
        
        Afterwards, delete the reminders from the file.
        """

        count_sent = 0

        for r in self.parsed_reminders:
            if r.should_send_today:
                print(f"DEBUG: {r.title}")
                if 'd' in r.modifiers:
                    print("Deleting")

                if 'c' in r.modifiers:
                    print("Executing")
                    continue

                r.send_email()

                count_sent += 1

        self.cab.put("remindmail", "sent_today", count_sent)

    def show_week(self):
        """
        Shows upcoming reminders for the week
        """

    def edit_reminders_file(self):
        """
        Edits the remind.md file
        You must configure the path to remind.md in

        cabinet -> path -> edit -> remind
        """

        try:
            self.cab.edit_file("remind")
        except FileNotFoundError:
            resolved = self.help_set_path_remindmd()
            if resolved:
                self.edit_reminders_file()
            else:
                sys.exit()


    def help_set_path_remindmd(self):
        """
        A fallback function when remind.md is not found.
        
        Returns:
            bool: whether the path to remind.md has been set
        """
        print(("You must configure the path to remind.md in "
                   "Cabinet. Run\n\n"
                   "`cabinet -p path edit remind value </full/path/to/remind.md>\n\n"))

        resp = ''
        while resp not in ['y', 'n']:
            resp = input((f"RemindMail can do this for you."
                            "Would you like to set this to "
                            f"{self.path_remind_file}/remind.md? y/n\n\n"))
            if resp == 'y':
                self.cab.put("path", "edit", "remind", "value",
                                f"{self.path_remind_file}/remind.md")
                print(("\n\nSet."))
                return True

            return False
