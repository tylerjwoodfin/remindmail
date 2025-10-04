"""
Utils for groups of reminders

This module provides functionality for managing and processing reminders, including parsing,
generating, and sending reminders based on various criteria. It handles YAML-based reminder
storage and integrates with email functionality for notification delivery.
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

def complete_file_input(text: str, state: int) -> str:
    """
    Provides tab completion for file paths in a command-line interface.

    Args:
        text (str): The initial text input by the user which may include unexpanded
            variables and partial file or directory names.
        state (int): The index of the item to return, which corresponds to the number
            of times the user has pressed the tab key.

    Returns:
        str: The nth file or directory name that matches the input text, where n is
            determined by the 'state' parameter.

    Raises:
        IndexError: If the 'state' index is out of the range of available completions.
    """
    text = os.path.expanduser(os.path.expandvars(text))
    return [x for x in glob.glob(text + '*')][state]

class ReminderManager:
    """
    A utility class for handling reminders and email operations.

    This class manages the lifecycle of reminders, including parsing from YAML files,
    generating and sending reminders, and handling reminder deletion. It integrates
    with a cabinet system for configuration and email functionality for notifications.
    """

    def __init__(self, remind_path_file: str | None = None) -> None:
        """
        Initializes the ReminderManager with configuration and setup.

        Args:
            remind_path_file (str | None): Optional path to the reminders YAML file.
                If not provided, will be retrieved from Cabinet.
        """
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

        Args:
            filename (str | None): Path to the YAML file containing reminders.
                If None, uses the configured remind_path_file.
            is_delete (bool): If True, will process reminders for deletion.
            is_print (bool): If True, will print reminder details to console.

        Returns:
            List[reminder.Reminder]: List of parsed Reminder objects.

        Raises:
            FileNotFoundError: If no filename is provided and remind_path_file is not set.
            yaml.YAMLError: If there is an error parsing the YAML file.
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

    @error_handler.ErrorHandler.exception_handler
    def generate(self, is_dry_run: bool, tags: Optional[List[str]] = None) -> None:
        """
        Generates and sends reminders for today, optionally deleting them after sending.

        This method parses the reminders file, filters by tags if specified, and sends
        the appropriate reminders. If a reminder is marked for deletion and should be
        sent today, it will be removed from the file after sending.

        Args:
            is_dry_run (bool): If True, only show what would be sent without actually sending.
            tags (Optional[List[str]]): Optional list of tags to filter reminders by.

        Raises:
            FileNotFoundError: If the reminders file cannot be found.
            yaml.YAMLError: If there is an error parsing the YAML file.
        """
        # First parse without deletion to get all reminders
        self.parse_reminders_file(is_delete=False)
        self.cabinet.log(f"Parsed {len(self.parsed_reminders)} reminders", level="info")
        
        # Filter reminders by tags if specified
        if tags:
            self.cabinet.log(f"Filtering by tags: {tags}", level="info")
            self.parsed_reminders = [
                r for r in self.parsed_reminders 
                if any(tag in r.tags for tag in tags)
            ]
            
        # Send reminders and handle deletion
        self.cabinet.log(f"{len(self.parsed_reminders)} with tags in: {tags}",
                         level="info")
        
        # Track which reminders need to be deleted
        reminders_to_delete = []
        
        for reminder in self.parsed_reminders:
            if reminder.should_send_today:
                if is_dry_run:
                    reminder_output = f"\n[yellow]Would send reminder[/yellow]" 
                    if reminder.delete:
                        reminder_output += f"[red] and delete after sending[/red]"
                    reminder_output += f":\n{reminder}"
                    self.console.print(reminder_output)
                    self.cabinet.log(reminder_output, level="info", is_quiet=True)
                else:
                    reminder.send()
                    if reminder.delete:
                        reminders_to_delete.append(reminder)
                        self.cabinet.log(f"Marked for deletion: {reminder}", level="info")
        
        # If any reminders need to be deleted, parse the file again with deletion enabled
        if reminders_to_delete and not is_dry_run:
            self.cabinet.log(f"Deleting {len(reminders_to_delete)} reminders after sending", level="info")
            self.parse_reminders_file(is_delete=True)

    def show_later(self) -> None:
        """
        Displays all reminders that are tagged as 'later'.

        This method shows the title and notes for each reminder that has been
        marked for later viewing. If no reminders have been parsed yet, it will
        parse the reminders file first.
        """

        if not self.parsed_reminders:
            self.parse_reminders_file()

        for r in self.parsed_reminders:
            if r.key == ReminderKeyType.LATER:
                self.console.print(r.title, style="bold green")
                print(r.notes)

    def show_reminders_for_days(self, limit: int = 8, tags: Optional[List[str]] = None) -> None:
        """
        Displays reminders scheduled for the upcoming specified number of days.

        Args:
            limit (int): The number of days to display reminders for. Defaults to 8.
            tags (Optional[List[str]]): Optional list of tags to filter reminders by.

        The display includes:
        - The date and day of the week
        - Reminder titles with appropriate styling
        - Tags associated with each reminder
        - Notes for each reminder
        - A "No Reminders" message if no reminders are scheduled for a day
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
                # Hide past warning if we're looking at a future date (not today)
                hide_past_warning: bool = day > date.today() + timedelta(days=1)
                if r.get_should_send_today(day, hide_past_warning = hide_past_warning):
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
        Opens the reminders YAML file for editing.

        This method uses the configured editor to open the reminders file for manual editing.
        The path to the file must be configured in Cabinet under:
        cabinet -> remindmail -> path -> file

        Raises:
            FileNotFoundError: If the reminders file path is not configured.
        """

        if self.remind_path_file is None:
            raise FileNotFoundError
        self.cabinet.edit_file(self.remind_path_file)

    def help_set_path_remindmd(self) -> bool:
        """
        Ensures the remindmail.yml file path is properly configured.

        This method checks if the path to remindmail.yml is set, and if not,
        it sets up a default path and creates the necessary file and directories.
        It also updates Cabinet accordingly.

        Returns:
            bool: True if the path was set or updated, False otherwise.

        Raises:
            FileNotFoundError: If the remindmail.yml file cannot be found and no
                default path can be established.
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

    def send_later(self) -> None:
        """
        Sends an email containing all reminders tagged as 'later'.

        This method collects all reminders marked for later viewing and sends them
        in a formatted email. The email includes the current date and a bulleted
        list of reminders with their titles and notes.

        If no 'later' reminders are found, a log message is generated to indicate this.
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

    def find_reminders(self, search_text: str) -> None:
        """
        Searches for reminders containing the given text in title, date, or day fields.
        If the search text is a valid date, also finds all reminders that would send on that date.

        Args:
            search_text (str): The text to search for in reminders.
        """
        if not self.parsed_reminders:
            self.parse_reminders_file()

        search_text = search_text.lower()
        found_reminders = set()  # Use set to avoid duplicates

        # Try to parse the search text as a date
        target_date = None
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%m-%d', '%m/%d', '%m/%d/%Y']:
                try:
                    target_date = datetime.strptime(search_text, fmt).date()
                    break
                except ValueError:
                    continue
        except ValueError:
            pass

        for reminder in self.parsed_reminders:
            # If we have a valid date, check if reminder would send on that date
            if target_date and reminder.get_should_send_today(target_date):
                found_reminders.add(reminder)
                continue

            # Search in title
            if search_text in reminder.title.lower():
                found_reminders.add(reminder)
                continue

            # Search in date or day value
            if reminder.value and search_text in str(reminder.value).lower():
                found_reminders.add(reminder)
                continue

            # Search in day of week
            if reminder.key in [
                ReminderKeyType.MONDAY, ReminderKeyType.TUESDAY,
                ReminderKeyType.WEDNESDAY, ReminderKeyType.THURSDAY,
                ReminderKeyType.FRIDAY, ReminderKeyType.SATURDAY,
                ReminderKeyType.SUNDAY
            ] and search_text in reminder.key.label.lower():
                found_reminders.add(reminder)
                continue

        if found_reminders:
            self.console.print(f"\nFound {len(found_reminders)} reminder{\
                's' if len(found_reminders) > 1 else ''} containing or sending on '{search_text}':\n", 
                style="bold green")
            for reminder in found_reminders:
                self.console.print(reminder.title, style="bold green")
                self.console.print(reminder, style="bold blue")
                if reminder.notes:
                    self.console.print(reminder.notes, style="italic")
                print()
        else:
            self.console.print(f"\nNo reminders found containing '{search_text}'" + \
                (f" or sending on {target_date}" if target_date else "") + "\n", 
                style="bold yellow")
