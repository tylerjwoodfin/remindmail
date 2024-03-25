"""
The main entrypoint
"""

import sys
import argparse

from . import reminder_manager

def handle_args(manager: reminder_manager.ReminderManager) -> None:
    """
    Parse arguments passed to RemindMail
    """

    parser = argparse.ArgumentParser(description="A tool to schedule and organize reminders")

    parser.add_argument("-ls",
        "--list",
        action="store_true",
        help="list all reminders",
    )
    parser.add_argument(
        "-g",
        "--generate",
        action="store_true",
        help="generate reminders.",
    )
    parser.add_argument("--later",
        action="store_true",
        help="show reminders scheduled for later"
    )
    parser.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="edits the remindmail file")

    try:
        args = parser.parse_args()

        if args.list:
            manager.print_reminders_file()
        elif args.generate:
            manager.generate()
        elif args.later:
            manager.show_later()
        elif args.edit:
            manager.edit_reminders_file()

        # no arguments
        if len(sys.argv) == 1:
            parser.print_help()

            sys.exit(1)

    except KeyboardInterrupt as exc:
        raise KeyboardInterrupt from exc

def main():
    """
    The main function
    """

    utils = reminder_manager.ReminderManager()

    try:
        handle_args(utils)
    except KeyboardInterrupt:
        print("\n")

if __name__ == "__main__":
    main()
