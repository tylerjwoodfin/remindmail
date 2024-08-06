"""
The main entrypoint
"""

import argparse

from . import reminder_manager
from . import query_manager

def handle_args(manager_r: reminder_manager.ReminderManager,
                manager_q: query_manager.QueryManager) -> None:
    """
    Parse arguments passed to RemindMail
    """

    parser = argparse.ArgumentParser(description="A tool to schedule and organize reminders")

    # parameter arguments
    parser.add_argument(
        "--title",
        help="the title of your reminder",
        nargs="+",
        default=None
    )

    parser.add_argument(
        "--when",
        "--d",
        help="when the reminder should send, as natural language",
        nargs="?",
        const="")

    parser.add_argument(
        "--notes",
        "--n",
        help="notes for the body of the email",
        nargs="?",
        const=""
    )

    parser.add_argument(
        "--later",
        action="store_true",
        help="show reminders scheduled for later"
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="save reminder without confirmation"
    )

    # action arguments
    parser.add_argument(
        "--generate",
        "--g",
        action="store_true",
        help="generate reminders.",
    )

    parser.add_argument(
        "--edit",
        action="store_true",
        help="edit the remindmail file")

    parser.add_argument(
        "--show-tomorrow",
        "--st",
        action="store_true",
        help="show a list of reminders scheduled for tomorrow",
    )

    parser.add_argument(
        "--send-later",
        "--sl",
        action="store_true",
        help="sends a list of reminders scheduled for `later`"
    )

    parser.add_argument(
        "--show-week",
        "--sw",
        action="store_true",
        help="show reminders through next 7 days",
    )

    try:
        args = parser.parse_args()

        if args.generate:
            manager_r.generate()
        elif args.later:
            manager_r.show_later()
        elif args.edit:
            manager_r.edit_reminders_file()
        elif args.show_tomorrow:
            manager_r.show_reminders_for_days(2)
        elif args.show_week:
            manager_r.show_reminders_for_days()
        elif args.send_later:
            manager_r.send_later()
        else:
            # handle title
            title = args.title
            if isinstance(title, list):
                title = ' '.join(title)
            elif isinstance(title, str):
                title = title.strip()

            manager_q.wizard_manual_reminder(
                title=title,
                when=args.when,
                notes=args.notes,
                save=args.save
            )

    except KeyboardInterrupt as exc:
        raise KeyboardInterrupt from exc

def main():
    """
    The main function
    """

    manager_remind = reminder_manager.ReminderManager()
    manager_query = query_manager.QueryManager(manager_remind)

    try:
        handle_args(manager_remind, manager_query)
    except KeyboardInterrupt:
        print("\n")

if __name__ == "__main__":
    main()
