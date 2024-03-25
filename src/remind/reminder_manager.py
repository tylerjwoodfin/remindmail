"""
Utils for groups of reminders
"""

import re
import os
import sys
from typing import List, Optional, Dict
from rich.console import Console
from cabinet import Cabinet, Mail
from . import reminder, error_handler

class ReminderManager:
    """
    A utility class for handling reminders and email operations.
    """

    def __init__(self) -> None:

        # file and data management
        self.cab = Cabinet()

        # DEBUG
        # file path for reminders
        # self.path_remind_file: str = self.cab.get('path', 'remindmail', 'file')
        # self.path_remind_file: str = 'src/remind/remind.md'
        self.path_remind_file: str = None

        # for sending emails
        self.mail = None

        # colors 🎨
        self.console = Console()

        self.parsed_reminders: List[reminder.Reminder] = []

    @error_handler.ErrorHandler.exception_handler
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

        reminders: List[reminder.Reminder] = []
        current_notes: List[str] = []
        new_lines: List[str] = []
        delete_current_reminder: bool = False

        # handle filename
        if filename is None:
            raise FileNotFoundError

        self.cab.log(f"Parsing reminders in {filename}")

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

        self.parsed_reminders = reminders

        return reminders

    @error_handler.ErrorHandler.exception_handler
    def generate(self) -> None:
        """
        Sends or executes reminders from the file that are scheduled to send today 
        (per parse_reminders_file).
        
        Afterwards, delete the reminders from the file.
        """

        if not self.parsed_reminders:
            self.parse_reminders_file()

        count_sent = 0

        if self.mail is None:
            self.mail = Mail()

        self.cab.log("Generating Reminders")
        for r in self.parsed_reminders:
            if r.should_send_today:
                self.cab.log(r)

                if 'c' in r.modifiers:
                    print("Executing")
                    continue

                r.mail = self.mail
                r.send_email()

                count_sent += 1

        self.cab.put("remindmail", "sent_today", count_sent, is_print=True)

    def show_later(self) -> None:
        """
        Shows all reminders tagged as 'later'
        """

        if not self.parsed_reminders:
            self.parse_reminders_file()

        for r in self.parsed_reminders:
            if r.reminder_type == 'later':
                self.console.print(r.title, style="bold green")
                print(r.notes)

    def show_week(self):
        """
        Shows upcoming reminders for the week
        """

    @error_handler.ErrorHandler.exception_handler
    def edit_reminders_file(self) -> None:
        """
        Edits the remind.md file
        You must configure the path to remind.md in

        cabinet -> path -> remindmail -> file
        """

        if self.path_remind_file is None:
            raise FileNotFoundError
        self.cab.edit_file(self.path_remind_file)

    def help_set_path_remindmd(self) -> bool:
        """
        A fallback function when remind.md is not found.
        
        Returns:
            bool: whether the path to remind.md has been set
        """
        if self.path_remind_file is None:

            fallback = ("\nRemindMail needs this path.\n"
                        "Please run `cabinet -p path remindmail file </path/to/remind.md>`\n"
                        "to set the path.")

            resp = input(("\nHi there! Your reminders will be stored in a file named "
                        "`remind.md`.\nThe location of remind.md will be stored using "
                        "Cabinet.\nPlease enter the full path to this file:\n"))

            if resp == '':
                print(fallback)
                sys.exit(0)

            if os.path.exists(resp):
                self.path_remind_file = resp
            else:
                create_resp = input((f"'{resp}' does not exist. "
                                        "Would you like to create it? (y/n):\n"))
                if create_resp.startswith('y'):
                    try:
                        # Attempt to create the file and its directories
                        os.makedirs(os.path.dirname(resp), exist_ok=True)
                        # create empty file
                        with open(resp, 'w', encoding='utf-8'):
                            pass
                        print(f"File created successfully: {resp}")
                    # pylint: disable=W0718
                    except Exception as e:
                        print(f"Failed to create the file: {e}")
                        print(fallback)
                        sys.exit(0)
                else:
                    print(fallback)
                    sys.exit(0)

        resp = ''
        self.path_remind_file = self.path_remind_file.replace("remind.md", "")

        if self.path_remind_file.endswith('/'):
            self.path_remind_file = self.path_remind_file.rstrip('/')

        if os.path.isdir(self.path_remind_file):
            old_value = self.path_remind_file
            new_value = f"{self.path_remind_file}/remind.md"
            self.path_remind_file = new_value
            self.cab.log(
                "Updating path -> remindmail -> file in "
                f"Cabinet from '{old_value}' to '{new_value}'"
            )
            self.cab.put("path", "remindmail", "file",
                         self.path_remind_file,
                         is_print=True
            )
            return True

        return False
