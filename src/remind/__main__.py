"""
The main entrypoint
"""

from pathlib import Path
import sys
import argparse
from remind.remindmail_utils import RemindMailUtils  # pylint: disable=wrong-import-position
from remind.remindmail import RemindMail  # pylint: disable=wrong-import-position
from remind.trello_manager import TrelloManager  # pylint: disable=wrong-import-position
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    """
    Parses command line arguments and performs the appropriate action based on the arguments passed.
    """

    help_offset = """Calculates the offset for a certain date (today by default)

		`remind -o <type (day,week,month)> <target date (YYYY-MM-DD), optional> <n>`
		(type is day, week, month)
		(n is 'every n days')

		Take the results of this function and use it to add an offset to a function.
		If you want something to happen every 3 days starting tomorrow, use:
		`remind -o day <tomorrow's date YYYY-MM-DD> 3`. See README.md for other examples."""

    parser = argparse.ArgumentParser()

    parser.add_argument('-m', '--message', nargs='?',
                        const='', help='Specify reminder message')
    parser.add_argument('-d', '--date', nargs='?', const='',
                        help='Specify reminder date')
    parser.add_argument('-n', '--notes', action='store_true',
                        help='Notes for the body of the email (or description of Jira task)')
    parser.add_argument('-ls', '--list', action='store_true',
                        help='List all reminders')
    parser.add_argument('-g', '--generate', action='store_true',
                        help='Generate reminders. By default, only generates every 12 hours.')
    parser.add_argument('--force', action='store_true',
                        help='Force reminders to be generated. Only used with -g.')
    parser.add_argument('--noconfirm', action='store_true',
                        help='Skip the confirmation before a reminder is scheduled/sent.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print generated reminders without sending them. Only used with -g.')
    parser.add_argument('--later', action='store_true',
                        help='Mail reminders for later')
    parser.add_argument('--stats', action='store_true',
                        help='Prints RemindMail usage statistics')
    parser.add_argument('-o', '--offset', nargs='?',
                        help=help_offset)
    parser.add_argument('-e', '--edit', action='store_true',
                        help='Edits remind.md through the terminal')
    parser.add_argument('--show-tomorrow', action='store_true',
                        help='Shows a list of reminders scheduled for tomorrow')
    parser.add_argument('--sent-today', action='store_true',
                        help='Prints the sum of reminders sent today (yesterday, if before 4AM)')
    parser.add_argument('manual_reminder_args', nargs='*')
    parser.add_argument('-j', '--jira', action='store_true',
                        help='Creates an issue through Jira rather than using email.')
    parser.add_argument('--type', nargs='?', const='task',
                        help=('Specify the Jira issue '
                              'type ("story", "task", "bug", "spike", "epic")'))
    parser.add_argument('--desc', '--description', nargs='?',
                        help='Jira issue description')
    parser.add_argument('--label', nargs='?',
                        help='Jira label')

    # Trello-specific Arguments
    parser.add_argument(
        "--trello-lists", "-tl", dest="trello_lists",
        action="store_true", help="Shows the lists on the board.")
    parser.add_argument(
        "--trello-items", "-ti", dest="trello_items",
        action="store_true", help="Shows items within a list.")
    parser.add_argument(
        "--trello-add", "-ta", dest="add_item",
        action="store_true", help="Add an item to the selected list.")
    parser.add_argument("--board", "-b", dest="trello_board",
                        type=str, nargs="?", help="Trello Board")
    parser.add_argument(
        "--list_index", dest="list_index", type=int, nargs="?", help="Index of the list.")
    parser.add_argument(
        "--list-name", dest="list_name", type=str, nargs="?", help="Name of the list.")
    parser.add_argument(
        "--item-name", "-i", dest="item_name", nargs="*", help="Name of the item to add.")

    try:
        args = parser.parse_args()

        # handle Trello
        if args.trello_lists:
            TrelloManager(board_name=args.trello_board).show_lists()
        elif args.add_item:
            trello = TrelloManager(board_name=args.trello_board)
            list_name = args.list_name
            if list_name is not None:
                for index, list_item in enumerate(trello
                                                .show_lists(is_quiet=True)):
                    if list_item['name'].lower() == list_name.lower():
                        list_index = index
            if list_index is None:
                print("Choose a list:\n")
                trello.show_lists()
                list_index = int(input("\n")) - 1

            item_name = ' '.join(args.item_name) or input(
                "\nWhat would you like to add?\n")

            TrelloManager(board_name=args.trello_board).add_item(
                list_index, item_name)
        elif args.trello_items and args.trello_items != "":
            trello = TrelloManager(board_name=args.trello_board)
            list_index = args.list_index
            list_name = args.list_name
            if list_name is not None:
                for index, list_item in enumerate(trello
                                                .show_lists(is_quiet=True)):
                    if list_item['name'].lower() == list_name.lower():
                        list_index = index
            if list_index is None:
                print("Choose a list:\n")
                trello.show_lists()
                list_index = int(input("\n")) - 1

            trello.show_items(list_index)

        # handle other arguments
        else:
            if args.list:
                RemindMailUtils().print_reminders_file()
            elif args.generate:
                RemindMail().generate(force=args.force, dry_run=args.dry_run)
            elif args.later:
                RemindMailUtils().mail_reminders_for_later()
            elif args.stats:
                RemindMailUtils().print_stats()
            elif args.offset is not None:
                RemindMailUtils().offset(args.offset.split(" "))
            elif args.edit:
                RemindMailUtils().edit_reminders_file()
            elif args.show_tomorrow:
                RemindMail().show_date()
            elif args.show_week:
                RemindMail().show_week()
            elif args.sent_today:
                print(RemindMailUtils().get_sent_today())
            elif args.jira:
                RemindMailUtils().create_jira_issue(
                    args.message or ' '.join(args.manual_reminder_args),
                    args.desc or None, args.type or None, args.label)
            elif args.manual_reminder_args:
                RemindMail().parse_query(query=' '.join(args.manual_reminder_args),
                                        noconfirm=args.noconfirm)
            else:
                RemindMail().manual_reminder(manual_message=args.message or '',
                                            manual_date=args.date or '', noconfirm=args.noconfirm)
    except KeyboardInterrupt:
        print("\n")
        sys.exit()


if __name__ == '__main__':
    main()
