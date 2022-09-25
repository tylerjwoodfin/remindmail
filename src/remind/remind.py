"""
The main file containing most of the logic. `client` and `client_utils` deal
specifically with Google Reminders, whereas this file contains the rest.
"""

from logging import exception
import os
import sys
import re
import time
from datetime import datetime
from datetime import timedelta
from remind import client
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from securedata import securedata, mail


TODAY = str(datetime.today().strftime('%Y-%m-%d'))
PATH_LOCAL = securedata.getItem(
    'path', 'remindmail', 'local')
PATH_CLOUD = securedata.getItem(
    'path', 'remindmail', 'cloud')
IS_CLOUD_ENABLED = PATH_LOCAL and PATH_CLOUD
HELP_TEXT = f"""\nUsage: remindmail <command>\n\n<command>:
	pull
    generate force
    generate force test
	config local <localPath>
	config cloud
	config cloudpath
	offset

	For help with a specific command: remindmail help <command>

Parameters (in brackets):
	taskInfo: enter any task you want to complete. Enclose in quotes, e.g. remindmail add 'take the trash out'
	localPath: Currently {PATH_LOCAL}. Settings are stored in {securedata.getConfigItem('path_securedata')} and should be stored as a JSON object (path -> remindmail -> local).

Notes Directory:
	remind.md in {PATH_LOCAL}. Change the path by running "remindmail config notes <fullPath>" (stored in {securedata.getConfigItem('path_securedata')})

remind.md:
	when generate() is run (from crontab or similar task scheduler; not intended to be run directly), matching tasks are emailed.
	See the provided example remind.md in ReadMe.

	"""


def _months_since_epoch(epoch):
    epoch_time = time.localtime(epoch)
    return ((epoch_time.tm_year - 1970) * 12) + epoch_time.tm_mon


def _strip_to(query):
    if query.startswith(' to ') or query.startswith('to ') or query.startswith('day to '):
        return ''.join(query.split('to')[1:]).strip()

    return query.strip()


def _parse_date(string):
    try:
        parsed_date = parse(string, fuzzy_with_tokens=True)
        return parsed_date

    except ValueError:
        return False


def log(message, level="info"):
    """A wrapper for securedata.log to handle the remindmail log setting"""

    path = securedata.getItem("path", "remindmail", "log") or securedata.setItem("path", "remindmail", "log",
                                                                                 securedata.getItem("path", "log") or "log")
    path = f"{path}/{TODAY}"
    securedata.log(message, level=level, filePath=path)
    return


def ls(s=None):
    """
    Displays the scheduled reminders in remind.py, formatted with line numbers
    Usage: remindmail ls
    Parameters:
    - s: string; currently unused. Passing 'help' will only return the help information for this function.
    """

    if s == "help":
        return f"Displays the scheduled reminders in remind.py (in {securedata.getItem('path', 'remindmail', 'local')}), formatted with line numbers\n\nUsage: remindmail ls"

    remindmd_cloud = f"{securedata.getItem('path', 'remindmail', 'cloud')}/remind.md"
    remindmd_local = f"{securedata.getItem('path', 'remindmail', 'local')}/remind.md"
    print("\n")
    os.system(
        f"rclone copyto {remindmd_cloud} {remindmd_local}; cat -n {remindmd_local}")
    print("\n")


def _send(subject, body, is_test, method="Terminal"):
    """A helper function to call mail.send"""

    print(f"Sending: {subject}")

    if body:
        subject = f"{subject} [See Notes]"

    body += f"<br><br>Sent via {method}"

    if not is_test:
        mail.send(f"Reminder - {subject}", body or "")
    else:
        log(
            f"In test mode- mail would send subject '{subject}' and body '{body}'", level="debug")


def _larger(a, b):
    """A helper function to return the larger string"""

    return a if len(a) > len(b) else b


def generate_reminders_for_later():
    """Generates reminders with [any] at the start"""

    try:
        remindmd_file = securedata.getFileAsArray("remind.md", "notes")
    except exception as e:
        log("Could not read remind.md; Aborting", level="error")
        sys.exit("Could not read remind.md; Aborting")

    reminders_for_later = []
    for item in remindmd_file:
        if item.startswith("[any] "):
            reminders_for_later.append(f"<li>{item.split('[any] ')[1]}")

    mail_summary = "Just a heads up, these reminders are waiting for you!<br><br>"
    mail_summary += "".join(reminders_for_later)
    mail_summary += "<br><br>To remove these, edit <b>remind.md</b>."

    mail.send(
        f"Pending Reminder Summary: {datetime.today().strftime('%B %d, %Y')}", mail_summary)


def generate():
    """
    Generates tasks from the remind.md file in {path_local}.
    Intended to be run from crontab (try 'remindmail generate force' to run immediately)
    """

    day_of_month_reminders_generated = str(
        securedata.getItem("remindmail", "day_generated"))

    day_of_month_reminders_generated = day_of_month_reminders_generated if day_of_month_reminders_generated != '' else 0

    if (str(datetime.today().day) != day_of_month_reminders_generated and datetime.today().hour > 3) or (len(sys.argv) > 2 and sys.argv[2] == "force"):
        log("Generating tasks")

        is_test = False
        if len(sys.argv) > 3 and sys.argv[3] == "test":
            is_test = True

        epoch_day = int(time.time()/60/60/24)
        epoch_week = int(time.time()/60/60/24/7)
        epoch_month = int(datetime.today().month)

        try:
            remindmd_file = securedata.getFileAsArray(
                "remind.md", "notes")
        except exception:
            log(
                "Could not read remind.md; Aborting", level="error")
            sys.exit("Could not read remind.md; Aborting")

        _remindmd_file = remindmd_file.copy()
        for index, item in enumerate(_remindmd_file):

            # ignore anything outside of [*]
            if not re.match("\[(.*?)\]", item):
                continue

            _item = item
            is_match = False

            # handle notes
            item_notes = ''
            if ':' in item:
                item_notes = item.split(":")[1].strip()
                item = item.split(":")[0]

            # handle [*]n, where n is a number or "d"
            token = item.split("[")[1].split("]")[0]
            token_after = item.split("]")[1].split(" ")[0]

            if token_after == "d" or token_after == "0":
                token_after = "1"

            if token_after.isdigit():
                token_after = int(token_after)
            else:
                token_after = -1

            parsed_date = ""
            if not "%" in token and not "any" in token:
                parsed_date = parse(token, fuzzy_with_tokens=True)

            if parsed_date and datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) == parsed_date[0]:
                is_match = True
                _send(item.split(' ', 1)[1], item_notes, is_test, "remind.md")

            elif "%" in token:

                if item[1:4] in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']:
                    split_type = item[1:4]
                else:
                    split_type = item[1].lower()  # d, w, m
                split_factor = item.split("%")[1].split("]")[0]
                split_offset = 0

                # e.g. [D%4+1] for every 4 days, offset 1
                if "+" in split_factor:
                    split_offset = int(split_factor.split("+")[1])
                    split_factor = int(split_factor.split("+")[0])
                else:
                    split_factor = int(split_factor)

                try:
                    if split_type == "d" and epoch_day % split_factor == split_offset:
                        is_match = True
                        _send(item.split(' ', 1)[
                              1], item_notes, is_test, "remind.md")
                    elif split_type == "w" and datetime.today().strftime("%a") == 'Sun' and epoch_week % split_factor == split_offset:
                        is_match = True
                        _send(item.split(' ', 1)[
                              1], item_notes, is_test, "remind.md")
                    elif split_type == "m" and datetime.today().day == 1 and epoch_month % split_factor == split_offset:
                        is_match = True
                        _send(item.split(' ', 1)[
                              1], item_notes, is_test, "remind.md")
                    elif split_type in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']:
                        if datetime.today().strftime("%a").lower() == split_type and epoch_week % split_factor == split_offset:
                            is_match = True
                            _send(item.split(' ', 1)[
                                  1], item_notes, is_test, "remind.md")
                except Exception as e:
                    log(
                        f"Could not send reminder from remind.md: {e}", level="error")

            # handle deletion and decrementing
            if is_match:
                if token_after == 1:
                    log(f"Deleting item from remind.md: {item}")
                    if not is_test:
                        try:
                            remindmd_file.remove(_item)
                        except Exception as e:
                            log(
                                f"Could not remove from remind.md: {e}", level="error")
                    else:
                        log(f"(in test mode- not deleting {item})",
                            level="debug")
                elif token_after > 1:
                    remindmd_file[index] = (item.replace(
                        f"]{token_after} ", f"]{token_after-1} "))

        try:
            securedata.writeFile("remind.md", "notes",
                                 '\n'.join(remindmd_file))
            securedata.setItem("remindmail", "day_generated",
                               datetime.today().day)
        except exception as e:
            log("Could not rewrite remind.md", level="error")
        log("Generated tasks")
    else:
        log("Reminders have already been generated in the past 12 hours.")


def help():
    """Prints help information returned by passing 'help' as a string into other functions."""

    if len(sys.argv) > 2:
        func = params.get(sys.argv[2])
        if hasattr(func, '__name__'):
            print(func("help"))
    else:
        print(HELP_TEXT)


def pull(s=None):
    """
    Pulls reminders from Google, deletes them, and emails them
    to the address using the email in securedata (see README)
    """

    if s == "help":
        return f"Pulls reminders from Google, deletes them, and adds them to remind.md in path_local (currently {PATH_LOCAL})"

    try:
        print("Connecting to Google...")
        cli = client.RemindersClient()
        print("Connection established.")
        items = cli.list_reminders(5)
    except Exception as e:
        log(
            f"Could not pull reminders from Google: {e}", level="warn")
        sys.exit(-1)

    # pull remind.md from cloud
    if IS_CLOUD_ENABLED:
        os.system(
            f"rclone copy {PATH_CLOUD} {PATH_LOCAL}")

    # for each reminder, either add it to remind.md if > 1 day from now, or send an email now, then delete it
    for item in items:
        seconds_until_target = (
            item['target_date'] - datetime.now()).total_seconds()

        if seconds_until_target >= 86400 and not item["done"]:
            print(
                f"Moving {item['title']} to {PATH_LOCAL}/remind.md")

            try:
                with open(f"{PATH_LOCAL}/remind.md", 'a') as f:
                    f.write(f"\n{item['title']}")
            except Exception as e:
                log(
                    f"Could not write to remind.md: {e}", level="critical")
                sys.exit(-1)
        else:
            try:
                mail.send(f"Reminder - {item['title'].split(']d ')[1]}", "")
            except Exception as e:
                try:
                    mail.send(f"Reminder - {item['title']}", "")
                except Exception as e:
                    log(
                        f"Could not send reminder email: {e}", level="warn")

        # delete
        if cli.delete_reminder(reminder_id=item['id']):
            log(
                f"Pulled and deleted {item['title']} from Google Reminders")
        else:
            log(
                f"Could not delete {item['title']} from Google Reminders", level="warning")

    # sync possibly-modified remind.md
    if IS_CLOUD_ENABLED:
        os.system(
            f"rclone sync {PATH_LOCAL} {PATH_CLOUD}")

    print("Pull complete.")


def config(s=None):
    """
    An interactive way to set securedata variables. May be removed in a future updatetime.

    Parameters:
    - s: string; currently unused.

    Passing 'help' will only return the help information for this function.
    """

    if s == "help":
        return f"""remindmail config local <path>: Set your notes path (use full paths)
		e.g. remindmail config local /home/userdir/Dropbox/Notes
		(this is stored SecureData; see README)

		remindmail config cloud: Set your cloud storage provider based on your rclone config (must have rclone- see ReadMe)
		e.g. remindmail config cloud
		(this is stored SecureData; see README)

		remindmail config cloudpath <path>: Set the path in your cloud service to store reminders (remind.md)
		e.g., if you keep Tasks in Dropbox at Documents/notes/remind.md: remindmail config cloudpath Documents/Notes
		(this is stored SecureData; see README)"""
    if len(sys.argv) < 3:
        print(config("help"))
        return

    if sys.argv[2].lower() == "local":
        new_dir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
        securedata.setItem("path", "remindmail", "local", new_dir)
        print(
            f"remind.md should now be stored in {new_dir}.")

    if sys.argv[2].lower() == "cloud":
        new_dir = sys.argv[3] if sys.argv[3][-1] == '/' else sys.argv[3] + '/'
        securedata.setItem("path", "remindmail", "cloud", new_dir)
        print(
            f"remind.md should now be synced in rclone through {new_dir}.")


def offset(s=None):
    """
    Calculates the offset for a certain date (today by default)

    Parameters:
    - s: string; currently unused.

    Passing 'help' will only return the help information for this function.
    """

    if s == "help":
        return """Calculates the offset for a certain date (today by default)

		remindmail offset <type> <date (YYYY-MM-DD, optional)> <n>
		(type is day, week, month)
		(n is 'every n days')

		Take the results of this function and use it to add an offset to a function.
		If you want something to happen every 3 days starting tomorrow, use:
		remindmail offset day <tomorrow's date YYYY-MM-DD> 3

		If the answer is 2, then you can add this to remind.md:
		[D%3+2] Task here

		e.g. remindmail offset day 2022-12-31 12
		(find offset for every 12 days intersecting 2022-12-31)

		e.g. remindmail offset week 2022-12-31 3
		(every 3 weeks intersecting 2022-12-31)

		e.g. remindmail offset month 2022-12-31 4
		(every 4 months intersecting 2022-12-31)

		e.g. remindmail offset day 2022-12-31 5
		e.g. remindmail offset week 2022-12-31 6
		e.g. remindmail offset month 2022-12-31 7"""

    if len(sys.argv) < 4:
        print("Usage: remindmail offset <type (day,week,month)> <date (optional, YYYY-MM-DD)> <n, as in 'every n <type>'>\nExample: remindmail offset week 2021-05-20 2\nFor help: 'remindmail help offset'")
        return

    if len(sys.argv) > 4:
        epoch_time = int(datetime.strptime(
            sys.argv[3], "%Y-%m-%d").timestamp())
        offset_n = sys.argv[4]
    else:
        offset_n = sys.argv[-1]
        epoch_time = int(time.time())

    try:
        if not offset_n.isnumeric():
            raise IndexError

        offset_n = int(offset_n)
        if sys.argv[2] == "month":
            return_val = _months_since_epoch(epoch_time) % offset_n
        elif sys.argv[2] == "week":
            return_val = int(epoch_time/60/60/24/7) % offset_n
        elif sys.argv[2] == "day":
            return_val = int(epoch_time/60/60/24) % offset_n
        else:
            print(f"'{sys.argv[2]}' must be 'day', 'week', or 'month'.")
            return

        print(return_val)

        if offset_n == 1:
            print(
                f"Note: Anything % 1 is always 0. This is saying 'every single {sys.argv[2]}'.\nOffsets are used to make sure a task will run for a given {sys.argv[2]}. '%1' means it will always run, so no need for an offset.\nPlease see the README for details, or just run 'remindmail help offset'.")
        elif return_val == 0:
            print(
                "Note: The offset is 0, so a task for this date in remind.md will be added without an offset.")

    except ValueError:
        print(sys.argv[3])
        print("Date must be YYYY-MM-DD.")
    except IndexError:
        print(
            f"Missing <n>, as in 'every n {sys.argv[2]}s'\nUsage: remindmail offset {sys.argv[2]} {sys.argv[3]} nExample:\nFor help: 'remindmail help offset'")
        return


def edit():
    """
    Edits the remind.md file
    You must configure the path to remind.md in

    securedata -> settings.json -> path -> edit -> remind
    """

    status = securedata.editFile("remind")
    if status == -1:
        print(
            f"You must configure the path to remind.md in {securedata.PATH_SECUREDATA}/settings.json -> path -> edit -> remind.\n\n")

        resp = ''
        while resp not in ['y', 'n']:
            resp = input(
                f"Would you like to set this to {PATH_LOCAL}/remind.md? y/n\n\n")
            if resp == 'y':
                securedata.setItem("path", "edit", "remind",
                                   "value", f"{PATH_LOCAL}/remind.md")
                print(
                    f"\n\nSet. Open {securedata.PATH_SECUREDATA}/settings.json and set path -> edit -> remind -> sync to true to enable cloud syncing.")
    sys.exit()


def parse_query(manual_reminder_param='', manual_time=''):
    """Parses sys.argv to determine what to email or what to write to a file for later"""

    query = ' '.join(sys.argv[1:])
    query_time = ''
    query_notes = ''
    query_time_formatted = ''
    query_notes_formatted = ''
    is_recurring = False

    # parse body of email (optional)
    if ':' in query:
        query_notes = query.split(":")[1]
        query = query.split(":")[0]

    for item in ['me to ', 'to ', 'me ']:
        if item in query.lower() and len(query.split(item)[0]) < 3:
            query = re.sub(item, '', query, flags=re.IGNORECASE, count=1)

    # handle recurring reminders
    is_recurring_options = ["every [0-9]+", "every week", "every month",
                            "every day", "every sunday", "every monday",
                            "every tuesday", "every wednesday",
                            "every thursday", "every friday", "every saturday"]

    is_recurring = len(re.findall(
        '|'.join(is_recurring_options), query, flags=re.IGNORECASE)) > 0

    if is_recurring:
        weekdays = ['sunday', 'monday', 'tuesday',
                    'wednesday', 'thursday', 'friday', 'saturday']
        for weekday in weekdays:
            if weekday in query:
                query_time = weekday[0:3].lower()
                query_time_formatted = f"every {weekday.capitalize()}"
                query = re.sub('every', '', query, flags=re.IGNORECASE)
                query = re.sub(weekday, '', query, flags=re.IGNORECASE)

        options = [
            ('every ', 'in '),
            ('in day', 'in 1 day'),
            ('in week', 'in 1 week'),
            ('in month', 'in 1 month')
        ]
        for opt in options:
            query = re.sub(opt[0], opt[1], query, flags=re.IGNORECASE)

    # handle "in n months"
    _months = re.findall("in [0-9]+ months|in 1 month",
                         query, flags=re.IGNORECASE)

    if _months:
        _number_of_months = int(re.search(r'\d+', _months[0]).group())
        _newdate = (datetime.now().date() +
                    relativedelta(months=_number_of_months))
        _query_match = query.split(_months[0])
        query = _larger(_query_match[0], _query_match[1])

        if is_recurring:
            query_time = f"M%{_number_of_months}"
            _frequency = f"{f'{_number_of_months} ' if _number_of_months > 1 else ''}{'month' if _number_of_months == 1 else 'months'}"
            query_time_formatted = f"every {_frequency} starting {_newdate.strftime('%B %d')}"
        else:
            query_time = _newdate
            query_time_formatted = query_time.strftime('%A, %B %d')

    # handle "in n weeks"
    _weeks = re.findall("in [0-9]+ weeks|in 1 week",
                        query, flags=re.IGNORECASE)
    if _weeks:
        _number_of_weeks = int(re.search(r'\d+', _weeks[0]).group())
        query = re.sub(_weeks[0], f"in {_number_of_weeks * 7} days", query)

    # handle "in n days"
    _days = re.findall("in [0-9]+ days|in 1 day", query, flags=re.IGNORECASE)
    if _days:
        _number_of_days = int(re.search(r'\d+', _days[0]).group())
        _query_match = query.split(_days[0])
        query = _larger(_query_match[0], _query_match[1])

        _newdate = datetime.now().date() + timedelta(days=_number_of_days)
        if is_recurring:
            query_time = f"D%{_number_of_days}"
            query_time_formatted = f"every {_number_of_days} days starting {_newdate.strftime('%B %d')}"
        else:
            query_time = _newdate
            query_time_formatted = _newdate.strftime('%A, %B %d')

    if " at " in query or " on " in query or " next " in query:
        # look for weekdays using 'on {dayw}'
        for day in ['on sun',
                    'on mon',
                    'on tue',
                    'on wed',
                    'on thu',
                    'on fri',
                    'on sat',
                    'next sun',
                    'next mon',
                    'next tue',
                    'next wed',
                    'next thu',
                    'next fri',
                    'next sat',
                    'sunday',
                    'monday',
                    'tuesday',
                    'wednesday',
                    'thursday',
                    'friday',
                    'saturday']:

            if re.search(day, query, flags=re.IGNORECASE):

                _query_match = re.split(day, query, flags=re.IGNORECASE)
                query = _larger(_query_match[0], _query_match[1])

                query_time = day
                query_time = re.sub('on ', '', query_time, flags=re.IGNORECASE)
                query_time = re.sub('next ', '', query_time,
                                    flags=re.IGNORECASE)
                query_time = re.sub('day', '', query_time, flags=re.IGNORECASE)
                query_time_formatted = query_time.capitalize() + 'day'
                break

    # handle "tomorrow"
    if not query_time and re.search("tomorrow", query, flags=re.IGNORECASE):

        # "tomorrow" means "today" if it's before 3AM
        if datetime.now().hour > 3:
            _date_tomorrow = datetime.now() + timedelta(days=1)
            query_time = _date_tomorrow.strftime('%F')
            query_time_formatted = _date_tomorrow.strftime('%A, %B %d')
        _query_match = re.split("tomorrow", query, flags=re.IGNORECASE)
        query = _strip_to(_larger(_query_match[0], _query_match[1]))

    # handle other dates
    parsed_date = _parse_date(query)

    # handle manual time
    if manual_time:
        parsed_date = _parse_date(manual_time)

    if parsed_date and (not query_time or manual_time):
        query_time = parsed_date[0].strftime('%F')

        if not query_time_formatted:
            query_time_formatted = parsed_date[0].strftime('%A, %B %d')

        if manual_reminder_param:
            query = manual_reminder_param
        else:
            query = ''.join(
                _larger(parsed_date[1][0], parsed_date[1][1] if len(parsed_date[1]) > 1 else ""))
            query = _strip_to(''.join(query.rsplit(' on ', 1)) or query)

    # confirmation
    if query_notes:
        query_notes_formatted = f"\nNotes: {query_notes.strip()}\n"

    response = ''
    query = _strip_to(query.strip())

    if manual_reminder_param:
        query = manual_reminder_param

    while response not in ['y', 'n', 'r', 'l', 'm']:
        options = "(y)es\n(n)o\n(p)arse without time\n(r)eport\n(l)ater\n(m)anual"
        response = input(
            f"""\nYour reminder for {query_time_formatted or "right now"}:\n{query}\n{query_notes_formatted or ''}\nOK?\n\n{options}\n\n""")

        if response == 'p':
            query_time = ''
            query_time_formatted = ''
            query = ' '.join(sys.argv[1:])
            print("\n------------------------------")

        elif response == 'l':
            query_time = 'any'
            is_recurring = True
            query_time_formatted = 'later'

        elif response == 'm':
            print("\n\n")
            manual_reminder_param()
            return

    if query_time:
        if len(response) > 0 and not response.startswith('n'):
            if response == 'r':
                print("Reporting bad query via email...")
                log(
                    f"RemindMail query reported: {' '.join(sys.argv[1:])}", level="warn")
                _send("Bad Query", ' '.join(sys.argv[1:]), False)
            else:
                print("Adding..." if response !=
                      'l' else "Saving for later...")
                query = query.strip()
                if query_notes:
                    query = f"{query}: {query_notes}"
                remind_md = securedata.getFileAsArray('remind.md', 'notes')
                remind_md.append(
                    f"[{query_time}]{'' if is_recurring else 'd'} {query}")
                securedata.writeFile("remind.md", "notes",
                                     '\n'.join(remind_md))
                log(f"""Scheduled "{query.strip()}" for {query_time_formatted}""")
        return

    if len(response) > 0 and not response.startswith('n'):
        if response == 'r':
            print("Reporting bad query via email...")
            log(
                f"RemindMail query reported: {' '.join(sys.argv[0:])}", level="warn")
            _send("Bad Query", ' '.join(sys.argv[0:]), False)
        else:
            _send(query.strip(), query_notes, False)


def manual_reminder():
    """Used to avoid errors, particularly when numbers are used that interfere with date parsing"""

    reminder = input("What's the reminder?\n")
    reminder_time = input(
        "\nWhen do you want to be reminded? (blank for now)\n")

    parse_query(reminder, reminder_time)


params = {
    "help": help,
    "pull": pull,
    "ls": ls,
    "config": config,
    "generate": generate,
    "later": generate_reminders_for_later,
    "offset": offset,
    "edit": edit
}


def main():
    """
    Generally parses all sys.argv parameters (such that `remind me to buy milk` is 
    feasible from the terminal
    """

    if len(sys.argv) > 1 and not (len(sys.argv) == 2 and sys.argv[1] == 'me'):
        func = params.get(sys.argv[1], lambda: parse_query())
        func()
    else:
        manual_reminder()


if __name__ == '__main__':
    main()
