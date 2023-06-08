"""
The main entrypoint
"""

from pathlib import Path
import sys
import argparse
from remind.remindmail_utils import RemindMailUtils  # pylint: disable=wrong-import-position
from remind.remindmail import RemindMail  # pylint: disable=wrong-import-position
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
    parser.add_argument('-ls', '-l', '--list', action='store_true',
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
    parser.add_argument('-t', '--type', nargs='?', const='task',
                        help='Specify the issue type ("story", "task", "bug", "spike", "epic")')
    parser.add_argument('--desc', '--description', nargs='?',
                        help='Jira issue description')
    parser.add_argument('--label', nargs='?',
                        help='Jira label')

    args = parser.parse_args()

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
        RemindMail().show_tomorrow()
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


if __name__ == '__main__':
    main()
