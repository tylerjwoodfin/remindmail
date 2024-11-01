"""
Utils for groups of reminders
"""

import re
import os
import subprocess
import sys
import glob
import readline
from datetime import date, timedelta, datetime
from typing import List, Optional
from rich.console import Console
from remind.reminder import ReminderKeyType
from cabinet import Cabinet, Mail
from . import reminder, error_handler

def complete_file_input(text, state):
    """
    Provides tab completion for file paths in a command-line interface.

    This function expands user and environment variables in the input path,
    then lists files and directories that match the expanded path. It is typically
    used to provide tab completion support for entering file locations, facilitating
    the user to quickly find and select files.

    Parameters:
    - text (str): The initial text input by the user which may include unexpanded
      variables and partial file or directory names.
    - state (int): The index of the item to return, which corresponds to the number
      of times the user has pressed the tab key.

    Returns:
    - str: The nth file or directory name that matches the input text, where n is
      determined by the 'state' parameter. Each subsequent press of the tab key
      increments the state, cycling through the list of possible completions.

    Raises:
    - IndexError: If the 'state' index is out of the range of available completions.
    """
    text = os.path.expanduser(os.path.expandvars(text))

    # List all files that match the current input
    return [x for x in glob.glob(text + '*')][state]

class ReminderManager:
    """
    A utility class for handling reminders and email operations.
    """

    def __init__(self) -> None:

        # file and data management
        self.cabinet = Cabinet()

        # DEBUG
        # file path for reminders
        self.path_remind_file: str | None = self.cabinet.get('path', 'remindmail', 'file')

        # for sending emails
        self.mail: Mail = Mail()

        # colors 🎨
        self.console = Console()

        # tab completion
        readline.set_completer_delims(' \t\n;')
        readline.set_completer(complete_file_input)
        readline.parse_and_bind('tab: complete')

        self.parsed_reminders: List[reminder.Reminder] = []

    @error_handler.ErrorHandler.exception_handler
    def parse_reminders_file(self, filename: str | None = None,
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
        filename = filename or self.path_remind_file

        if filename is None:
            raise FileNotFoundError

        self.cabinet.log(f"Parsing reminders in {filename}", is_quiet=True)

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

                    pattern_any_reminder = r"\[(.*?)\](c?d?)\s*(.*)"
                    pattern_date_key = r"(?:\d{4}-)?\d{2}-\d{2}"
                    pattern_dow_key = (
                        r"^(sun(day)?|"
                        r"mon(day)?|"
                        r"tue(sday)?|"
                        r"wed(nesday)?|"
                        r"thu(rsday)?|"
                        r"fri(day)?|"
                        r"sat(urday)?)$"
                    )

                    match = re.match(pattern_any_reminder, stripped_line)
                    if match:
                        details, reminder_modifiers, title = match.groups()
                        details = details.lower()

                        details = details.split(",")

                        # get reminder type
                        try:
                            reminder_key = \
                                ReminderKeyType.from_db_value(details[0])
                        except ValueError:
                            # allow for [{date}] and [{dow}]
                            if re.match(pattern_date_key, details[0]):
                                reminder_key = ReminderKeyType.DATE
                            elif re.match(pattern_dow_key, details[0]):
                                reminder_key = ReminderKeyType.DAY_OF_WEEK
                                reminder_value = details[0]

                            else:
                                self.cabinet.log(
                                    f"'{details[0]}' in '{line}' is not a valid Reminder key.",
                                    level="warn")
                                continue

                        reminder_value: Optional[str] = None
                        reminder_frequency: Optional[int] = None
                        reminder_offset: int = 0

                        # handle reminders of type 'sun' - 'sat'
                        if reminder_key == ReminderKeyType.DAY_OF_WEEK:
                            reminder_frequency = 1
                            reminder_value = details[0]
                            if len(details) > 1:
                                reminder_frequency = int(details[1])
                            reminder_offset = int(details[2]) if len(details) > 2 else 0
                        elif reminder_key == ReminderKeyType.DAY_OF_MONTH:
                            reminder_value = details[1] or "1"
                        elif reminder_key in [ReminderKeyType.DAY,
                                               ReminderKeyType.WEEK,
                                               ReminderKeyType.MONTH]:
                            reminder_frequency = int(details[1]) if len(details) > 1 else None
                            reminder_offset = int(details[2]) if len(details) > 2 else 0
                        elif reminder_key == ReminderKeyType.LATER:
                            reminder_value = "later"
                        else:
                            reminder_value = details[0]  # for specific dates

                        r = reminder.Reminder(reminder_key,
                                                  reminder_value,
                                                  reminder_frequency,
                                                  reminder_offset,
                                                  reminder_modifiers,
                                                  title.strip(),
                                                  '',
                                                  self.cabinet,
                                                  mail=self.mail,
                                                  path_remind_file=self.path_remind_file)

                        r.should_send_today = r.get_should_send_today()

                        if is_delete and r.should_send_today and 'd' in reminder_modifiers:
                            delete_current_reminder = True
                            self.cabinet.log(f"Will Delete: {r}")
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

        lines_to_delete: List[int] = []

        if not self.parsed_reminders:
            self.parse_reminders_file()

        count_sent = 0

        if self.mail is None:
            self.mail = Mail()

        self.cabinet.log("Generating Reminders")
        for index, r in enumerate(self.parsed_reminders):
            if r.should_send_today:
                self.cabinet.log(str(r), is_quiet=True)

                if 'd' in r.modifiers:
                    # mark the reminder line for deletion
                    lines_to_delete.append(index)

                    if r.notes:
                        # add the lines for each note to lines_to_delete
                        note_line_count = len(r.notes.splitlines())
                        lines_to_delete.extend(
                            range(index + 1, index + 1 + note_line_count)
                        )

                # handle commands
                if 'c' in r.modifiers:
                    self.cabinet.log(
                            f"Executing command: {r.title}", level="debug"
                        )
                    try:
                        # add path so things like `cabinet` calls work from crontab
                        home_dir = os.path.expanduser("~")
                        path_local_bin = os.path.join(home_dir, ".local/bin")
                        os.environ[
                            "PATH"
                        ] = f"{path_local_bin}:{os.environ['PATH']}"

                        cmd_output = subprocess.check_output(
                            r.title, shell=True, universal_newlines=True
                        )
                        self.cabinet.log(
                            f"Results: {cmd_output}", level="debug"
                        )
                    except subprocess.CalledProcessError as error:
                        self.cabinet.log(
                            f"Command execution failed with exit code: {error.returncode}",
                            level="error",
                        )
                        self.cabinet.log(
                            f"Error output: {error.output}", level="error"
                        )
                    continue

                r.mail = self.mail
                r.send_email()

                count_sent += 1

        # Remove lines corresponding to sent reminders from the reminders file.
        # This method should safely update the file
        # by removing only the lines listed in lines_to_delete.
        self.delete_reminders(lines_to_delete)

        self.cabinet.put("remindmail", "sent_today", count_sent, is_print=True)

    def show_later(self) -> None:
        """
        Shows all reminders tagged as 'later'
        """

        if not self.parsed_reminders:
            self.parse_reminders_file()

        for r in self.parsed_reminders:
            if r.key == ReminderKeyType.LATER:
                self.console.print(r.title, style="bold green")
                print(r.notes)

    def show_reminders_for_days(self, limit: int = 8) -> None:
        """
        Displays reminders scheduled for the upcoming <limit> days.

        This method calculates the dates for the next <limit> days, starting from tomorrow
        (today if between midnight and 4am),
        and it checks each day for scheduled reminders. For each day, it prints the date
        and any corresponding reminders. If there are no reminders for a specific day,
        it indicates so. Reminders with specific modifiers change the display style
        to highlight their importance or category.
        """

        current_time = datetime.now().time()
        start_day_offset = 0 if current_time.hour < 4 else 1

        # Prepare the next 7 days
        dates = [date.today() + timedelta(days=i) for i in range(
            start_day_offset, limit)]

        # Parse reminders file if necessary
        if not self.parsed_reminders:
            self.parse_reminders_file()

        # Iterate through each upcoming day
        for day in dates:
            formatted_date = day.strftime("%Y-%m-%d, %A")
            self.console.print(f"[bold blue on white]{formatted_date}", highlight=False)

            # Track the number of reminders shown for the day
            reminder_shown = False

            # Display each reminder scheduled for this day
            for r in self.parsed_reminders:
                if r.get_should_send_today(day):
                    reminder_style = f"bold {'purple' if 'c' in r.modifiers else 'green'}"
                    self.console.print(r.title, style=reminder_style, highlight=False)
                    if r.notes:
                        self.console.print(r.notes, style="italic")
                    reminder_shown = True

            if not reminder_shown:
                self.console.print("No Reminders", style="dim")

            self.console.print("")

    @error_handler.ErrorHandler.exception_handler
    def edit_reminders_file(self) -> None:
        """
        Edits the remind.md file
        You must configure the path to remind.md in

        cabinet -> path -> remindmail -> file
        """

        if self.path_remind_file is None:
            raise FileNotFoundError
        self.cabinet.edit_file(self.path_remind_file)

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
        path: str = self.path_remind_file or self.cabinet.get('path', 'remindmail', 'file') or ""
        self.path_remind_file = path.replace("remind.md", "")

        if self.path_remind_file.endswith('/'):
            self.path_remind_file = self.path_remind_file.rstrip('/')

        if os.path.isdir(self.path_remind_file):
            old_value = self.path_remind_file
            new_value = f"{self.path_remind_file}/remind.md"
            self.path_remind_file = new_value
            self.cabinet.log(
                "Updating path -> remindmail -> file in "
                f"Cabinet from '{old_value}' to '{new_value}'"
            )
            self.cabinet.put("path", "remindmail", "file",
                         self.path_remind_file,
                         is_print=True
            )
            return True

        return False

    def send_later(self):
        """
        Sends an email containing reminders
        tagged as `later`
        """

        if not self.parsed_reminders:
            self.parse_reminders_file()

        today = date.today().strftime('%Y-%m-%d')

        # get a bulleted list of all 'later' reminders
        self.cabinet.log("Getting 'later' reminders")

        reminders = ""
        for r in self.parsed_reminders:
            if r.key == ReminderKeyType.LATER:
                reminders += f"• {r.title}<br>"
                if r.notes:
                    reminders += f"  - {r.notes}<br>"

        if reminders:
            email_body = f"Here are your reminders for later:<br>{reminders}"

            self.mail.send(f"Reminders for Later, {today}",
                        email_body)
        else:
            self.cabinet.log("No reminders were found for 'later'.")

    @error_handler.ErrorHandler.exception_handler
    def delete_reminders(self, lines_to_delete):
        """
        Deletes specific lines from the reminders file.

        Parameters:
        - lines_to_delete (List[int]): List of line indices to be deleted from the reminders file.
        """

        path: str = self.path_remind_file or self.cabinet.get('path', 'remindmail', 'file') or ""
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        with open(path, "w", encoding="utf-8") as file:
            for index, line in enumerate(lines):
                if index not in lines_to_delete:
                    file.write(line)

        return False
