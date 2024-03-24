"""
Utils for groups of reminders
"""

import re
import os
import sys
from typing import List, Optional, Dict
from rich.console import Console
from cabinet import Cabinet, Mail
from . import reminder

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
        self.parsed_reminders = self.parse_reminders_file('src/remind/remind.md')

        # colors 🎨
        self.console = Console()

    def parse_reminders_file(self, filename: str = None,
                             is_delete: bool = False) -> List[reminder.Reminder]:
        """
        Parses a markdown file containing reminders into an array of Reminder objects.

        Each line of the file is expected to define a reminder or
        a note associated with the preceding reminder.
        Comments and empty lines are ignored.
        The reminders are parsed based on predefined formats and
        accumulated into Reminder objects, which are then returned in a list.

        After parsing Reminders into a List, delete
        reminders scheduled for today with a "d" modifier from the file.
        This deletion removes the reminder and any notes associated with it
        until the next reminder line is encountered.

        Args:
            filename (str, optional): The path to the markdown file containing the reminders.
                If unset, defaults to self.path_remind_file
            is_delete (bool, optional): If enabled, delete all reminders scheduled for
                today that are also scheduled for deletion.

        Returns:
            List[Reminder]: A list of Reminder objects parsed from the file.
        """

        self.cab.log(f"Parsing reminders in {filename}")

        reminders: List[reminder.Reminder] = []
        current_notes: List[str] = []
        new_lines: List[str] = []
        delete_current_reminder: bool = False

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
                stripped_line = line.strip()

                if stripped_line.startswith("["):
                    # save previous reminder notes
                    if current_notes and not delete_current_reminder:
                        reminders[-1].notes = "\n".join(current_notes)
                        current_notes = []  # reset notes for next reminder
                    else:
                        delete_current_reminder = False

                    pattern = r"\[(.*?)\](c?d?)\s*(.*)"
                    match = re.match(pattern, stripped_line)
                    if match:
                        details, modifiers, title = match.groups()

                        details = details.split(",")
                        reminder_type: str = details[0]
                        reminder_date: Optional[str] = None
                        cycle: Optional[int] = None
                        offset: int = 0

                        if reminder_type in day_to_int:
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

                        r = reminder.Reminder(reminder_type,
                                                  reminder_date,
                                                  cycle,
                                                  offset,
                                                  modifiers,
                                                  title.strip(),
                                                  '',
                                                  self.cab,
                                                  self.mail)
                        r.should_send_today = r.get_should_send_today()

                        if is_delete and r.should_send_today and 'd' in modifiers:
                            delete_current_reminder = True
                            self.cab.log(f"Will Delete: {r}")
                        else:
                            new_lines.append(line)  # Add non-deleted reminders back

                        reminders.append(r)
                elif not delete_current_reminder:
                    if not stripped_line and not current_notes:
                        new_lines.append(line)
                    else:
                        current_notes.append(stripped_line)
                        new_lines.append(line)

        if current_notes:  # catch notes for the last reminder
            reminders[-1].notes = "\n".join(current_notes)

        # Rewrite the file without deleted reminders
        if is_delete:
            with open(filename, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)

        return reminders

    def generate(self):
        """
        Sends or executes reminders from the file that are scheduled to send today 
        (per parse_reminders_file).
        
        Afterwards, delete the reminders from the file.
        """

        count_sent = 0

        self.cab.log("Generating Reminders")
        for r in self.parsed_reminders:
            if r.should_send_today:
                self.cab.log(r)

                if 'c' in r.modifiers:
                    print("Executing")
                    continue

                r.send_email()

                count_sent += 1

        self.cab.put("remindmail", "sent_today", count_sent, is_print=True)

    def show_later(self):
        """
        Shows all reminders tagged as 'later'
        """

        for r in self.parsed_reminders:
            if r.reminder_type == 'later':
                self.console.print(r.title, style="bold green")
                print(r.notes)

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
