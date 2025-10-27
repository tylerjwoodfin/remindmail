"""
Handles YAML parsing and writing for reminders
"""

from typing import List, Dict, Any
import yaml
from .reminder import Reminder, ReminderKeyType


class YAMLManager:
    """
    Manages YAML operations for reminders
    """

    @staticmethod
    def parse_yaml_file(filename: str) -> List[Dict[str, Any]]:
        """
        Parses a YAML file containing reminders.

        Args:
            filename (str): Path to the YAML file

        Returns:
            List[Dict[str, Any]]: List of reminder dictionaries
        """
        with open(filename, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            if data is None:
                data = {}
            return data.get("reminders", [])

    @staticmethod
    def write_yaml_file(filename: str, reminders: List[Dict[str, Any]]) -> None:
        """
        Writes reminders to a YAML file.

        Args:
            filename (str): Path to the YAML file
            reminders (List[Dict[str, Any]]): List of reminder dictionaries
        """
        data = {"reminders": reminders}
        with open(filename, "w", encoding="utf-8") as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False)

    @staticmethod
    def reminder_to_dict(reminder: Reminder) -> Dict[str, Any]:
        """
        Converts a Reminder object to a dictionary for YAML storage.

        Args:
            reminder (Reminder): The reminder to convert

        Returns:
            Dict[str, Any]: Dictionary representation of the reminder
        """
        reminder_dict = {
            "name": reminder.title,
            "delete": reminder.delete,
            "command": reminder.command,
            "notes": reminder.notes,
        }

        # Add tags if present
        if reminder.tags:
            reminder_dict["tags"] = reminder.tags

        # Add email if present
        if reminder.email:
            reminder_dict["email"] = reminder.email

        # Handle different reminder types
        if reminder.key == ReminderKeyType.LATER:
            reminder_dict["later"] = True
        elif reminder.key == ReminderKeyType.DATE:
            reminder_dict["date"] = reminder.value
        elif reminder.key == ReminderKeyType.DAY_OF_MONTH:
            if reminder.value and isinstance(reminder.value, int):
                reminder_dict["dom"] = int(reminder.value)
            else:
                raise ValueError(
                    "Reminder day of month cannot be empty and must be an "
                    "integer for day of month reminders."
                )
        elif reminder.key in [
            ReminderKeyType.MONDAY,
            ReminderKeyType.TUESDAY,
            ReminderKeyType.WEDNESDAY,
            ReminderKeyType.THURSDAY,
            ReminderKeyType.FRIDAY,
            ReminderKeyType.SATURDAY,
            ReminderKeyType.SUNDAY,
        ]:
            reminder_dict["day"] = reminder.key.db_value
            if reminder.frequency and reminder.frequency > 1:
                reminder_dict["every"] = reminder.frequency
        elif reminder.key == ReminderKeyType.DAY:
            reminder_dict["every"] = reminder.frequency or 1
            reminder_dict["unit"] = "days"
        elif reminder.key == ReminderKeyType.WEEK:
            reminder_dict["every"] = reminder.frequency or 1
            reminder_dict["unit"] = "weeks"
        elif reminder.key == ReminderKeyType.MONTH:
            reminder_dict["every"] = reminder.frequency or 1
            reminder_dict["unit"] = "months"

        # Add offset if present
        if reminder.offset:
            reminder_dict["offset"] = reminder.offset

        # Add notes if present
        if reminder.notes:
            reminder_dict["notes"] = reminder.notes

        return reminder_dict

    @staticmethod
    def dict_to_reminders(
        reminder_dict: Dict[str, Any], cabinet, mail, path_remind_file: str
    ) -> list[Reminder]:
        """
        Converts a dictionary to a list of Reminder objects.

        Args:
            reminder_dict (Dict[str, Any]): Dictionary containing reminder data
            cabinet: Cabinet instance
            mail: Mail instance
            path_remind_file (str): Path to the reminders file

        Returns:
            list[Reminder]: List of Reminder objects
        """
        reminders = []

        # Get tags if present
        tags = reminder_dict.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]

        # Get email if present
        email = reminder_dict.get("email", None)

        # Create reminder based on type
        if "later" in reminder_dict:
            reminders.append(
                Reminder(
                    key=ReminderKeyType.LATER,
                    title=reminder_dict["name"],
                    value=None,
                    frequency=None,
                    starts_on=None,
                    offset=0,
                    delete=reminder_dict.get("delete", False),
                    command=reminder_dict.get("command", ""),
                    notes=reminder_dict.get("notes", ""),
                    index=0,
                    cabinet=cabinet,
                    mail=mail,
                    path_remind_file=path_remind_file,
                    tags=tags,
                    email=email,
                )
            )
        elif "date" in reminder_dict:
            reminders.append(
                Reminder(
                    key=ReminderKeyType.DATE,
                    title=reminder_dict["name"],
                    value=reminder_dict["date"],
                    frequency=None,
                    starts_on=None,
                    offset=0,
                    delete=reminder_dict.get("delete", False),
                    command=reminder_dict.get("command", ""),
                    notes=reminder_dict.get("notes", ""),
                    index=0,
                    cabinet=cabinet,
                    mail=mail,
                    path_remind_file=path_remind_file,
                    tags=tags,
                    email=email,
                )
            )
        elif "dom" in reminder_dict:
            reminders.append(
                Reminder(
                    key=ReminderKeyType.DAY_OF_MONTH,
                    title=reminder_dict["name"],
                    value=reminder_dict["dom"],
                    frequency=None,
                    starts_on=None,
                    offset=0,
                    delete=reminder_dict.get("delete", False),
                    command=reminder_dict.get("command", ""),
                    notes=reminder_dict.get("notes", ""),
                    index=0,
                    cabinet=cabinet,
                    mail=mail,
                    path_remind_file=path_remind_file,
                    tags=tags,
                    email=email,
                )
            )
        elif "day" in reminder_dict:
            day = reminder_dict["day"]
            # Handle comma-separated days
            if "," in day:
                keys = ReminderKeyType.from_csv_values(day)
            else:
                keys = [ReminderKeyType.from_db_value(day)]

            for key in keys:
                reminders.append(
                    Reminder(
                        key=key,
                        title=reminder_dict["name"],
                        value=None,
                        frequency=reminder_dict.get("every", 1),
                        starts_on=None,
                        offset=reminder_dict.get("offset", 0),
                        delete=reminder_dict.get("delete", False),
                        command=reminder_dict.get("command", ""),
                        notes=reminder_dict.get("notes", ""),
                        index=0,
                        cabinet=cabinet,
                        mail=mail,
                        path_remind_file=path_remind_file,
                        tags=tags,
                        email=email,
                    )
                )
        elif "every" in reminder_dict:
            unit = reminder_dict.get("unit", "days")
            if unit == "weeks":
                key = ReminderKeyType.WEEK
            elif unit == "months":
                key = ReminderKeyType.MONTH
            else:
                key = ReminderKeyType.DAY

            reminders.append(
                Reminder(
                    key=key,
                    title=reminder_dict["name"],
                    value=None,
                    frequency=reminder_dict["every"],
                    starts_on=None,
                    offset=reminder_dict.get("offset", 0),
                    delete=reminder_dict.get("delete", False),
                    command=reminder_dict.get("command", ""),
                    notes=reminder_dict.get("notes", ""),
                    index=0,
                    cabinet=cabinet,
                    mail=mail,
                    path_remind_file=path_remind_file,
                    tags=tags,
                    email=email,
                )
            )

        return reminders
