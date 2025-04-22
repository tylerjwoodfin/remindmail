"""
Utils for groups of reminders
"""

import os
import glob
import readline
from datetime import date, timedelta, datetime
from typing import Any, Dict, List, Optional
from rich.console import Console
from remind.reminder import ReminderKeyType
from remind.yaml_manager import YAMLManager
from cabinet import Cabinet, Mail
import yaml
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

    def __init__(self, remind_path_file: str | None = None) -> None:

        # file and data management
        self.cabinet = Cabinet()

        # file path for reminders
        self.remind_path_file: str | None = remind_path_file or \
            self.cabinet.get('remindmail', 'path', 'file')

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
                         is_delete: bool = False,
                         is_print: bool = False) -> List[reminder.Reminder]:
        """
        Parses a YAML file containing reminders into an array of Reminder objects.
        """
        filename = filename or self.remind_path_file

        if filename is None:
            raise FileNotFoundError

        self.cabinet.log(f"Parsing reminders in {filename}", is_quiet=True)

        try:
            reminder_dicts = YAMLManager.parse_yaml_file(filename)
        except yaml.YAMLError as e:
            self.cabinet.log(f"Error parsing reminders in {filename}: {e}", level="error")
            return []

        reminders: List[reminder.Reminder] = []
        new_reminders: List[Dict[str, Any]] = []

        for reminder_dict in reminder_dicts:
            parsed_reminders = YAMLManager.dict_to_reminders(reminder_dict, self.cabinet, self.mail, filename)

            should_keep = False
            for r in parsed_reminders:
                r.should_send_today = r.get_should_send_today()
                if is_delete and r.should_send_today and r.delete:
                    self.cabinet.log(f"Will Delete: {r}")
                else:
                    should_keep = True
                    reminders.append(r)

            if not is_delete or should_keep:
                new_reminders.append(reminder_dict)

        if is_delete:
            YAMLManager.write_yaml_file(filename, new_reminders)

        self.parsed_reminders = reminders

        if is_print:
            for r in reminders:
                self.console.print(r.title, style="bold green")
                self.console.print(r, style="bold blue")
                if r.notes:
                    self.console.print(r.notes, style="italic")
                    print()

        return reminders

    def write_reminder(self, reminder: reminder.Reminder) -> None:
        """
        Writes a reminder to the YAML file.
        
        Args:
            reminder (Reminder): The reminder to write
        """
        # Read existing reminders
        if not self.remind_path_file:
            raise ValueError("remind_path_file is not set. Set with `cabinet -p remindmail path file <path>`")

        reminder_dicts = YAMLManager.parse_yaml_file(self.remind_path_file)
        
        # Convert new reminder to dict
        new_reminder_dict = YAMLManager.reminder_to_dict(reminder)
        
        # Add new reminder
        reminder_dicts.append(new_reminder_dict)
        
        # Write back to file
        YAMLManager.write_yaml_file(self.remind_path_file, reminder_dicts)

    @error_handler.ErrorHandler.exception_handler
    def generate(self, is_dry_run: bool, tags: Optional[List[str]] = None) -> None:
        """
        Generates and sends reminders for today.
        
        Args:
            is_dry_run (bool): If True, only show what would be sent without actually sending
            tags (Optional[List[str]]): Optional list of tags to filter reminders by
        """
        self.parse_reminders_file()
        self.cabinet.log(f"Parsed {len(self.parsed_reminders)} reminders", level="info")
        
        # Filter reminders by tags if specified
        if tags:
            self.cabinet.log(f"Filtering by tags: {tags}", level="info")
            self.parsed_reminders = [
                r for r in self.parsed_reminders 
                if any(tag in r.tags for tag in tags)
            ]
            
        # Send reminders
        self.cabinet.log(f"{len(self.parsed_reminders)} with tags in: {tags}",
                         level="info")
        for reminder in self.parsed_reminders:
            if reminder.should_send_today:
                if is_dry_run:
                    self.console.print(f"[yellow]Would send reminder:\n[/yellow] {reminder}")
                    self.cabinet.log(f"Would send reminder: {reminder}", level="info", is_quiet=True)
                else:
                    reminder.send()

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

    def show_reminders_for_days(self, limit: int = 8, tags: Optional[List[str]] = None) -> None:
        """
        Displays reminders scheduled for the upcoming <limit> days.

        Args:
            limit (int): The number of days to display reminders for
            tags (Optional[List[str]]): Optional list of tags to filter reminders by
        """

        current_time = datetime.now().time()
        start_day_offset = 0 if current_time.hour < 4 else 1

        # Prepare the next 7 days
        dates = [date.today() + timedelta(days=i) for i in range(
            start_day_offset, limit)]

        # Parse reminders file if necessary
        if not self.parsed_reminders:
            self.parse_reminders_file()

        # Filter reminders by tags if specified
        if tags:
            self.parsed_reminders = [
                r for r in self.parsed_reminders 
                if any(tag in r.tags for tag in tags)
            ]

        # Iterate through each upcoming day
        for day in dates:
            formatted_date = day.strftime("%Y-%m-%d, %A")
            if tags:
                formatted_date = f"{formatted_date} -> {tags}"
            self.console.print(f"[bold blue on white]{formatted_date}[/bold blue on white]",
                               highlight=False)

            # Track the number of reminders shown for the day
            reminder_shown = False

            # Display each reminder scheduled for this day
            for r in self.parsed_reminders:
                if r.get_should_send_today(day):
                    reminder_style = f"bold {'purple' if r.command else 'green'}"
                    reminder_title = f"{r.title}"
                    reminder_tags = ""
                    if r.tags:
                        formatted_tags = f"\n    - #{', #'.join(r.tags)}"
                        reminder_tags = f"[bold blue]{formatted_tags}[/bold blue]"
                    self.console.print(f"- {reminder_title} {reminder_tags}", 
                                       style=reminder_style, highlight=False)
                    if r.notes:
                        self.console.print(r.notes, style="italic")
                    reminder_shown = True

            if not reminder_shown:
                self.console.print("No Reminders", style="dim")

            self.console.print("")

    @error_handler.ErrorHandler.exception_handler
    def edit_reminders_file(self) -> None:
        """
        Edits the remindmail.yml file
        You must configure the path to remindmail.yml in

        cabinet -> remindmail -> path -> file
        """

        if self.remind_path_file is None:
            raise FileNotFoundError
        self.cabinet.edit_file(self.remind_path_file)

    def help_set_path_remindmd(self) -> bool:
        """
        A fallback function to ensure remindmail.yml is set
        to a default path if not configured.

        Returns:
            bool: whether the path to remindmail.yml has been set
        """
        default_path = os.path.expanduser('~/remindmail/remindmail.yml')

        # Check if the path is not set
        if not self.remind_path_file:
            # Assign default path
            self.remind_path_file = default_path

            # Check if the default path exists; if not, create the file and its directories
            if not os.path.exists(default_path):
                os.makedirs(os.path.dirname(default_path), exist_ok=True)
                with open(default_path, 'w', encoding='utf-8') as file:
                    yaml.dump({'reminders': []}, file)

            # Store the path in Cabinet
            self.cabinet.put('remindmail', 'path', 'file', default_path)

            print(
                "Reminders will be stored in ~/remindmail/remindmail.yml.\n"
                "You can change this at any time by running:\n"
                "`cabinet -p remindmail path file <full path to remindmail.yml>`\n"
                "or simply `cabinet -e` and modifying the remindmail object.\n"
            )

            return True

        path = self.remind_path_file or self.cabinet.get('remindmail', 'path', 'file') or ""
        self.remind_path_file = path.replace("remindmail.yml", "")

        # Ensure we have a directory and it ends correctly
        if not self.remind_path_file:
            raise FileNotFoundError(
                "Cannot find remindmail.yml. Set with `cabinet -p remindmail path file <path>`")

        if self.remind_path_file.endswith('/'):
            self.remind_path_file = self.remind_path_file.rstrip('/')

        # Update path in Cabinet if it points to a directory
        if os.path.isdir(self.remind_path_file):
            old_value = self.remind_path_file
            new_value = f"{self.remind_path_file}/remindmail.yml"
            self.remind_path_file = new_value
            self.cabinet.log(
                "Updating remindmail -> path -> file in "
                f"Cabinet from '{old_value}' to '{new_value}'"
            )
            self.cabinet.put("remindmail", "path", "file", self.remind_path_file, is_print=True)
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
