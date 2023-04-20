"""
Contains standalone helper functions
"""

import os
import sys
import time
import datetime
from typing import List
import requests
import pytz
from cabinet import Cabinet, Mail


class RemindMailUtils:
    """
    Contains standalone helper functions
    """

    cab = Cabinet()
    path_remind_file = cab.get(
        'path', 'remindmail', 'file')
    mail = Mail()
    query_trace: List[str] = []

    def get_user_time(self):
        """
        A helper function to return the epoch seconds based on the user's timezone
        """

        user_timezone = self.cab.get("remindmail", "timezone")
        if user_timezone is None:
            # get timezone based on IP
            print("Checking timezone...")
            response = requests.get('https://ipapi.co/json/', timeout=10)

            # Parse the response JSON to get the user's timezone
            if response.status_code == 200:
                data = response.json()
                user_timezone = self.cab.put("remindmail", "timezone", data.get('timezone'))
                print(f"Set timezone: {user_timezone}")
            else:
                print("Could not parse timezone; using UTC")
                return datetime.datetime.utcnow()

        timezone = pytz.timezone(user_timezone)

        now = datetime.datetime.now(timezone)

        # Get the UTC time
        utc_now = datetime.datetime.utcnow()

        # Calculate the time difference between the specified timezone and UTC
        offset = timezone.utcoffset(utc_now).total_seconds()

        # Subtract the offset from the current time
        utc_time = now + datetime.timedelta(seconds=offset)

        # Convert the UTC time to the number of seconds since January 1, 1970
        unix_time = int(utc_time.timestamp())

        return unix_time


    def print_reminders_file(self, param=None):
        """
        Displays the scheduled reminders in remind.py, formatted with line numbers
        Usage: remindmail ls
        Parameters:
        - param: string; currently unused

        Passing 'help' will only return the help information for this function.
        """

        if param == "help":
            return (f"Displays the scheduled reminders in remind.py"
                    f" (in {RemindMailUtils.path_remind_file}),"
                    " formatted with line numbers\n\nUsage: remindmail ls")

        remindmd_local = f"{RemindMailUtils.path_remind_file}/remind.md"

        if RemindMailUtils.path_remind_file is not None:
            os.system(f"cat -n {remindmd_local}")
        else:
            print(f"Could not find reminder path; in "
                  f"${RemindMailUtils.cab.path_cabinet}/settings.json, "
                  f"set path -> remindmail -> file to the absolute path of "
                  f"the directory of your remind.md file.")
            print("\n")

    def mail_reminders_for_later(self):
        """Mails a summary of reminders with [any] at the start from remind.md in {PATH_LOCAL}"""

        remindmd_file = RemindMailUtils.cab.get_file_as_array(
            "remind.md", "notes") or []
        reminders_for_later = []
        for item in remindmd_file:
            if item.startswith("[any] "):
                reminders_for_later.append(f"<li>{item.split('[any] ')[1]}")

        mail_summary = "Just a heads up, these reminders are waiting for you!<br><br>"
        mail_summary += "".join(reminders_for_later)
        mail_summary += "<br><br>To remove these, edit <b>remind.md</b>."

        date_formatted = datetime.datetime.today().strftime('%B %d, %Y')
        RemindMailUtils().send_email(
            f"Pending Reminder Summary: {date_formatted}", mail_summary, is_quiet=False)

    def offset(self, args):
        """
        Calculates the offset for a certain date (today by default)
        """

        def months_since_epoch(epoch):
            epoch_time = time.localtime(epoch)
            return ((epoch_time.tm_year - 1970) * 12) + epoch_time.tm_mon

        if len(args) < 2:
            print(f"""Error: 'remind -o {args[0] or ''}' missing required arguments:
    remind -o '<type (day,week,month)> <target date (YYYY-MM-DD), optional> <n>'\
    \n\nRun `remind -h` for details.""")
            return

        if len(args) >= 2:
            epoch_time = int(datetime.datetime.strptime(
                args[1], "%Y-%m-%d").timestamp())
            offset_n = args[2]
        else:
            offset_n = args[-1]
            epoch_time = int(time.time())

        try:
            if not offset_n.isnumeric():
                raise IndexError

            offset_n = int(offset_n)
            token_example = "d"
            if args[0] == "month":
                token_example = "m"
                return_val = months_since_epoch(epoch_time) % offset_n
            elif args[0] == "week":
                token_example = "w"
                return_val = int(epoch_time/60/60/24/7) % offset_n
            elif args[0] == "day":
                return_val = int(epoch_time/60/60/24) % offset_n
            else:
                print(f"'{args[0]}' must be 'day', 'week', or 'month'.")
                return

            print(return_val)
            print(f"This means you can add '[{token_example}%{offset_n}+{return_val}] <task name>' \
to {RemindMailUtils.path_remind_file}/remind.md to match the selected date.")

            if offset_n == 1:
                print((f"Note: Anything % 1 is always 0. This is saying "
                       f"'every single {args[0]}'.\nOffsets are used to make sure a task will run"
                       f" for a given {args[0]}. '%1' means it will always run, so no need for an"
                       f" offset.\nPlease see the README for details, or"
                       f" run 'remindmail help offset'."))
            elif return_val == 0:
                print(("Note: The offset is 0, so a task for this date in remind.md "
                       "will be added without an offset."))

        except ValueError:
            print("Date must be YYYY-MM-DD.")
        except IndexError:
            print((f"Missing <n>, as in 'every n {args[0]}s'\n"
                   f"Usage: remindmail offset {args[0]} {args[1]} n"
                   f"\nFor help: 'remindmail help offset'"))
            return

    def edit_reminders_file(self):
        """
        Edits the remind.md file
        You must configure the path to remind.md in

        cabinet -> settings.json -> path -> edit -> remind
        """

        try:
            RemindMailUtils.cab.edit_file("remind")
        except FileNotFoundError:
            print((f"You must configure the path to remind.md in "
                   f"{RemindMailUtils.cab.path_cabinet}/settings.json -> "
                   f"path -> edit -> remind.\n\n"))

            resp = ''
            while resp not in ['y', 'n']:
                resp = input((f"Would you like to set this to "
                             f"{RemindMailUtils.path_remind_file}/remind.md? y/n\n\n"))
                if resp == 'y':
                    RemindMailUtils.cab.put("path", "edit", "remind", "value",
                                            f"{RemindMailUtils.path_remind_file}/remind.md")
                    print((f"\n\nSet. Open {RemindMailUtils.cab.path_cabinet}/settings.json"
                           f" and set path -> edit -> remind -> sync to true"
                           f" to enable cloud syncing."))
        sys.exit()

    def send_email(self, subject, body, method="Terminal", is_quiet=False):
        """A helper function to call mail.send"""

        print(f"Sending: {subject}")

        if body:
            subject = f"{subject} [See Notes]"

        body += f"<br><br>Sent via {method}"

        RemindMailUtils.mail.send(
            f"Reminder - {subject}", body or "", is_quiet=is_quiet)
        print("\nSent! Check your inbox.")
