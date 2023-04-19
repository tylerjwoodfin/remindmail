#!/bin/python3
"""
The main file containing most of the logic.
"""

import argparse
import os
import sys
import re
import time
from enum import Enum
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from cabinet import Cabinet, Mail


class GenerateType(Enum):
    """
    The options available for the `generate` function

    EMAIL will send each matching reminder
    LIST will print each matching reminder to the console
    """
    EMAIL = 'email'
    LIST = 'list'


cab = Cabinet()
mail = Mail()

TODAY = str(datetime.today().strftime('%Y-%m-%d'))
WEEKDAYS = ['sunday', 'monday', 'tuesday',
            'wednesday', 'thursday', 'friday', 'saturday']
PATH_REMIND_FILE = cab.get(
    'path', 'remindmail', 'file')
QUERY_TRACE = []


def _months_since_epoch(epoch):
    epoch_time = time.localtime(epoch)
    return ((epoch_time.tm_year - 1970) * 12) + epoch_time.tm_mon


def parse_date(query):
    """
    Parses a date from the input query
    """

    # handle 'tomorrow'
    if 'tomorrow' in query:
        _days = 0 if datetime.today().hour < 3 else 1
        query = (datetime.now() + timedelta(days=_days)).strftime('%F')

    try:
        parsed_date = parse(query, fuzzy_with_tokens=True)

        # handle dates in the past
        days_from_now = (parsed_date[0] - datetime.today()).days
        if days_from_now < -90:
            return (parsed_date[0] + relativedelta(years=1), parsed_date[1])

        return parsed_date

    except ValueError:
        return False


def log_msg(message, level="info", path=None, print_msg=False):
    """A wrapper for cab.log to handle the remindmail log setting"""

    path_log = cab.get("path", "log")
    path = path or path_log
    path = f"{path}/{TODAY}"

    QUERY_TRACE.append(message)

    if print_msg:
        print(message)

    cab.log(f"remindmail: {message}", level=level, file_path=path,
            is_quiet=level == "info")


def send_email(subject, body, is_test=False, method="Terminal", is_quiet=False):
    """A helper function to call mail.send"""

    print(f"Sending: {subject}")

    if body:
        subject = f"{subject} [See Notes]"

    body += f"<br><br>Sent via {method}"

    if not is_test:
        count_sent = cab.get("remindmail", "sent_today") or 0
        cab.put("remindmail", "sent_today", count_sent+1)
        log_msg(f"Incremented reminder count to {count_sent+1}")
        mail.send(f"Reminder - {subject}", body or "", is_quiet=is_quiet)
        print("\nSent! Check your inbox.")
    else:
        log_msg(
            f"In test mode- mail would send subject '{subject}' and body '{body}'", level="debug")


def list_reminders(param=None):
    """
    Displays the scheduled reminders in remind.py, formatted with line numbers
    Usage: remindmail ls
    Parameters:
    - param: string; currently unused

    Passing 'help' will only return the help information for this function.
    """

    if param == "help":
        return (f"Displays the scheduled reminders in remind.py"
                f" (in {PATH_REMIND_FILE}),"
                " formatted with line numbers\n\nUsage: remindmail ls")

    remindmd_local = f"{PATH_REMIND_FILE}/remind.md"

    if PATH_REMIND_FILE is not None:
        os.system(f"cat -n {remindmd_local}")
    else:
        print(f"Could not find reminder path; in ${cab.path_cabinet}/settings.json, set path \
            -> remindmail -> file to the absolute path of the directory of your remind.md file.")
    print("\n")


def mail_reminders_for_later():
    """Mails a summary of reminders with [any] at the start from remind.md in {PATH_LOCAL}"""

    remindmd_file = cab.get_file_as_array("remind.md", "notes") or []
    reminders_for_later = []
    for item in remindmd_file:
        if item.startswith("[any] "):
            reminders_for_later.append(f"<li>{item.split('[any] ')[1]}")

    mail_summary = "Just a heads up, these reminders are waiting for you!<br><br>"
    mail_summary += "".join(reminders_for_later)
    mail_summary += "<br><br>To remove these, edit <b>remind.md</b>."

    date_formatted = datetime.today().strftime('%B %d, %Y')
    send_email(
        f"Pending Reminder Summary: {date_formatted}", mail_summary, is_quiet=False)


def generate(force: bool = False, dry_run: bool = False,
             generate_date: int = None, generate_type: GenerateType = GenerateType.EMAIL):
    """
    Mails reminders from the remind.md file in {PATH_LOCAL}.
    Intended to be run from crontab (try 'remindmail generate force' to run immediately)
    """

    if generate_date is None:
        generate_date = datetime.today()

    today_index = generate_date.day

    day_of_month_reminders_generated = cab.get(
        "remindmail", "day_generated")

    if day_of_month_reminders_generated == '':
        day_of_month_reminders_generated = 0

    # do not generate more than once in one day unless `remind generate force`
    if not (today_index != day_of_month_reminders_generated
            and generate_date.hour > 3) and not force and not dry_run:
        log_msg(
            "Reminders have already been generated in the past 12 hours.", level="debug")
        return

    log_msg("Generating reminders")

    command = ''

    epoch_day = int(time.time()/60/60/24)
    epoch_week = int(time.time()/60/60/24/7)
    epoch_month = int(generate_date.month)

    remindmd_file = cab.get_file_as_array("remind.md", "notes") or []

    _remindmd_file = remindmd_file.copy()
    for index, item in enumerate(_remindmd_file):

        is_match = False
        is_command = False

        today_zero_time = generate_date.replace(
            hour=0, minute=0, second=0, microsecond=0)

        # handle commands
        if "]c" in item:
            is_command = True
            command = item.split("]c ")[1]

        # ignore anything outside of [*]
        if not re.match(r"\[(.*?)\]", item):
            continue

        _item = item

        # handle notes
        item_notes = ''
        if ':' in item:
            item_notes = ''.join(item.split(":")[1:]).strip()
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
            try:
                parsed_date = parse(token, fuzzy_with_tokens=True)
            except ValueError:
                try:
                    parsed_date = parse(
                        f"{token}day", fuzzy_with_tokens=True)
                except ValueError as error:
                    log_msg(
                        f"Could not parse token: {token}; {error}", level="error")

        if parsed_date and today_zero_time == parsed_date[0]:
            is_match = True

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

            is_epoch_equal_offset = (
                split_type == 'd' and epoch_day % split_factor == split_offset,
                split_type == 'w' and epoch_week % split_factor == split_offset,
                split_type == 'm' and epoch_month % split_factor == split_offset,
                split_type in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
                and epoch_week % split_factor == split_offset)

            today_dayw = generate_date.strftime("%a")

            split_types = ['d', 'w', 'm', 'sun', 'mon',
                           'tue', 'wed', 'thu', 'fri', 'sat']
            if split_type in split_types and any(is_epoch_equal_offset):
                if split_type == 'd':
                    is_match = True
                elif split_type == 'w' and today_dayw == 'Sun':
                    is_match = True
                elif split_type == 'm' and today_index == 1:
                    is_match = True
                elif (split_type in ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
                      and today_dayw.lower() == split_type):
                    is_match = True

        # handle deletion and decrementing
        if is_match:

            if not is_command:
                if generate_type == GenerateType.EMAIL:
                    send_email(item.split(' ', 1)[1],
                               item_notes, dry_run, "remind.md")
                elif generate_type == GenerateType.LIST:
                    print(item)
            if token_after == 1:
                log_msg(f"Deleting item from remind.md: {item}")
                if not dry_run:
                    try:
                        remindmd_file.remove(_item)
                    except ValueError as err:
                        log_msg(
                            f"Could not remove from remind.md: {err}", level="error")
                elif generate_type != GenerateType.LIST:
                    log_msg(f"(in test mode- not deleting {item})",
                            level="debug")
            elif token_after > 1:
                remindmd_file[index] = (item.replace(
                    f"]{token_after} ", f"]{token_after-1} "))

            if is_command:
                if not dry_run:
                    print("Executing command:\n", command)
                    os.system(command)
                else:
                    log_msg(f"(in test mode- not executing {item})",
                            level="debug")

    cab.write_file("remind.md", "notes",
                   '\n'.join(remindmd_file), is_quiet=True)

    if not dry_run:
        log_msg(f"Setting remindmail -> day_generated to {today_index}")
        cab.put("remindmail", "day_generated", today_index)
    elif generate_type != GenerateType.LIST:
        log_msg(
            f"In test mode- would set remindmail -> day_generated to {today_index}", level="debug")

    log_msg("Generated tasks")


def offset(args):
    """
    Calculates the offset for a certain date (today by default)
    """

    if len(args) < 2:
        print(f"""Error: 'remind -o {args[0] or ''}' missing required arguments:
remind -o '<type (day,week,month)> <target date (YYYY-MM-DD), optional> <n>'\
\n\nRun `remind -h` for details.""")
        return

    if len(args) >= 2:
        epoch_time = int(datetime.strptime(
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
            return_val = _months_since_epoch(epoch_time) % offset_n
        elif args[0] == "week":
            token_example = "w"
            return_val = int(epoch_time/60/60/24/7) % offset_n
        elif args[0] == "day":
            return_val = int(epoch_time/60/60/24) % offset_n
        else:
            print(f"'{args[0]}' must be 'day', 'week', or 'month'.")
            return

        print(return_val)
        print(f"""This means you can add '[{token_example}%{offset_n}+{return_val}] <task name>' \
to {PATH_REMIND_FILE}/remind.md to match the selected date.""")

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


def edit():
    """
    Edits the remind.md file
    You must configure the path to remind.md in

    cabinet -> settings.json -> path -> edit -> remind
    """

    try:
        cab.edit_file("remind")
    except FileNotFoundError:
        print((f"You must configure the path to remind.md in "
               f"{cab.path_cabinet}/settings.json -> path -> edit -> remind.\n\n"))

        resp = ''
        while resp not in ['y', 'n']:
            resp = input(
                f"Would you like to set this to {PATH_REMIND_FILE}/remind.md? y/n\n\n")
            if resp == 'y':
                cab.put("path", "edit", "remind",
                        "value", f"{PATH_REMIND_FILE}/remind.md")
                print((f"\n\nSet. Open {cab.path_cabinet}/settings.json"
                       f" and set path -> edit -> remind -> sync to true"
                       f" to enable cloud syncing."))
    sys.exit()


def show_tomorrow():
    """
    Prints reminders from remind.md tagged with tomorow's date in YYYY-MM-DD format
    """

    tomorrow = datetime.today() + timedelta(days=1)
    generate(force=True, dry_run=True, generate_date=tomorrow,
             generate_type=GenerateType.LIST)


def parse_query(query=None, manual_message='', manual_date='', noconfirm=False):
    """
    Parses arguments to determine what to email or what to write to a file for later.

    Args:
        query (str): The query string to parse (default: None).
        manual_message (str): The manual message to use if query is None (default: '').
        manual_date (str): The manual date to use (default: '').
        noconfirm (bool, optional): If True, bypass the confirmation screen.
    """

    # helper functions
    def get_larger(string_a, string_b):
        """A helper function to return the larger string between string_a and string_b"""

        return string_a if len(string_a) > len(string_b) else string_b

    def strip_to(query):
        """A helper function to remove the portion after 'to' or 'day to'"""
        if query.startswith(' to ') or query.startswith('to ') or query.startswith('day to '):
            return ''.join(query.split('to')[1:]).strip()

        return query.strip()

    query = query or manual_message
    query_original = query
    QUERY_TRACE.append(query)
    query_time_token = ''  # the 'meat' between [] in remind.md
    query_notes = ''
    query_time_formatted = ''
    query_notes_formatted = ''
    is_recurring = False

    def report_query():
        print("Reporting bad query via email...")
        log_msg(
            f"RemindMail query reported: {query_original}", level="warn")
        send_email(f"Bad Query: {TODAY}", '<br>'.join(
            QUERY_TRACE).replace("\n", "<br>"), False, is_quiet=False)

    if manual_date == 'now':
        manual_date = TODAY

    # parse for notes
    if ':' in query:
        query_notes = ''.join(query.split(":")[1:])
        query = query.split(":")[0]

    # remove filler text
    for item in ['me to ', 'to ', 'me ']:
        if item in query.lower() and len(query.split(item)[0]) < 3:
            query = re.sub(item, '', query, flags=re.IGNORECASE, count=1)

    # handle recurring reminders
    is_recurring_options = ["every [0-9]+", "every week", "every month",
                            "every day"] + [f"every {day}" for day in WEEKDAYS]

    is_recurring = any(re.findall(
        '|'.join(is_recurring_options), query, flags=re.IGNORECASE))

    if is_recurring:
        for weekday in WEEKDAYS:
            if weekday in query:
                query_time_token = weekday[0:3].lower()
                query_time_formatted = f"every {weekday.capitalize()}"

                # remove 'every *day' from query
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
        query = get_larger(_query_match[0], _query_match[1])

        if is_recurring:
            query_time_token = f"M%{_number_of_months}"
            _frequency = (f"{f'{_number_of_months} ' if _number_of_months > 1 else ''}"
                          f"{'month' if _number_of_months == 1 else 'months'}")
            query_time_formatted = f"every {_frequency} starting {_newdate.strftime('%B %d')}"
        else:
            query_time_token = _newdate
            query_time_format = '%A, %B %d'

            if _newdate.year != datetime.today().year:
                query_time_format = '%A, %B %d, %Y'
            query_time_formatted = _newdate.strftime(query_time_format)

    # handle "in n weeks"
    _weeks = re.findall("in [0-9]+ weeks|in 1 week",
                        query, flags=re.IGNORECASE)
    if _weeks:
        # reduce into "in n days"
        _number_of_weeks = int(re.search(r'\d+', _weeks[0]).group())
        query = re.sub(_weeks[0], f"in {_number_of_weeks * 7} days", query)

    # handle "in n days"
    _days = re.findall("in [0-9]+ days|in 1 day", query, flags=re.IGNORECASE)
    if _days:
        _number_of_days = int(re.search(r'\d+', _days[0]).group())
        _query_match = query.split(_days[0])
        query = get_larger(_query_match[0], _query_match[1])

        _newdate = datetime.now().date() + timedelta(days=_number_of_days)
        if is_recurring:
            query_time_token = f"D%{_number_of_days}"
            query_time_formatted = (f"every {_number_of_days} days"
                                    f" starting {_newdate.strftime('%B %d')}")
        else:
            query_time_token = _newdate
            query_time_format = '%A, %B %d'

            # if in a different year, append the year
            if _newdate.year != datetime.today().year:
                query_time_format = '%A, %B %d, %Y'
            query_time_formatted = _newdate.strftime(query_time_format)

    if " at " in query or " on " in query or " next " in query:

        # ['on sun', ... , 'on sat', 'next sun', ... , 'next sat']
        for day in [f"on {day[:3]}" for day in WEEKDAYS] + [f"next {day[:3]}" for day in WEEKDAYS]:

            if re.search(day, query, flags=re.IGNORECASE):

                _query_match = re.split(day, query, flags=re.IGNORECASE)
                query = get_larger(_query_match[0], _query_match[1])

                query_time_token = re.sub(
                    'on|next|day', '', day, flags=re.IGNORECASE).strip()

                query_time_formatted = {
                    'sun': 'Sunday',
                    'mon': 'Monday',
                    'tues': 'Tuesday',
                    'wednes': 'Wednesday',
                    'thurs': 'Thursday',
                    'fri': 'Friday',
                    'satur': 'Saturday'
                }.get(query_time_token, None)

                if query_time_formatted is None:
                    raise KeyError(
                        f"Error: '{query_time_token}' not matched to a weekday")

                break

    # handle other dates
    parsed_date = parse_date(query)

    # handle "tomorrow"
    if not query_time_token and re.search("tomorrow", query, flags=re.IGNORECASE):
        _query_match = re.split("tomorrow", query, flags=re.IGNORECASE)
        query = strip_to(get_larger(_query_match[0], _query_match[1]))

    # handle manual time
    if manual_date:
        parsed_date = parse_date(manual_date)

    # handle specific dates (found or specified)
    if parsed_date and (not query_time_token or manual_date):
        query_time_token = parsed_date[0].strftime('%F')

        if not query_time_formatted and manual_date != TODAY:
            query_time_format = '%A, %B %d'

            if parsed_date[0].year != datetime.today().year:
                query_time_format = '%A, %B %d, %Y'

            query_time_formatted = parsed_date[0].strftime(query_time_format)

        if manual_message:
            query = manual_message
        else:
            if len(parsed_date[1]) > 1:
                _join_operator = ''
                if len(parsed_date[1]) > 1:
                    _join_operator = parsed_date[1][1]
                query = ''.join(get_larger(parsed_date[1][0], _join_operator))
                query = strip_to(''.join(query.rsplit(' on ', 1)) or query)
            elif len(parsed_date) > 1:
                parsed_date_formatted = strip_to(''.join(parsed_date[1]))
                if parsed_date_formatted:
                    query = parsed_date_formatted

    # confirmation
    if query_notes:
        query_notes_formatted = f"\nNotes: {query_notes.strip()}\n"

    response = ''
    query = strip_to(query.strip())

    if manual_message:
        query = manual_message

    while response not in ['y', 'n', 'r', 'l', 'm']:
        options = "(y)es\n(n)o\n(p)arse entire query\n(r)eport\n(l)ater\n(t)omorrow\n(m)anual"

        query_time_formatted = query_time_formatted or 'right now'

        if not noconfirm:
            prompt = (f"""\nYour reminder for {query_time_formatted}:"""
                      f"\n{query}\n{query_notes_formatted or ''}\nOK?\n\n{options}\n\n")
            QUERY_TRACE.append(prompt)

            response = input(prompt)
            QUERY_TRACE.append(response)
        else:
            response = 'y'

        if response == 'p':
            query_time_token = ''
            query_time_formatted = ''
            query = query_original
            print("\n------------------------------")
            QUERY_TRACE.append("\n------------------------------")

        elif response == 'l':
            query_time_token = 'any'
            is_recurring = True
            query_time_formatted = 'later'

        elif response == 'm':
            print("\n\n")
            manual_reminder()
            return

        elif response == 't':
            days = ["Monday", "Tuesday", "Wednesday",
                    "Thursday", "Friday", "Saturday", "Sunday"]
            weekday = days[(datetime.now() + timedelta(days=1)).weekday()]
            manual_reminder(query, weekday)
            return

    # send immediate reminders
    if query_time_formatted == 'right now' and response == 'y':
        send_email(query.strip(), query_notes, False, is_quiet=True)
        return

    # scheduled reminders
    if query_time_token:
        if len(response) > 0 and not response.startswith('n'):
            if response == 'r':
                report_query()
            else:
                # add to remind.md file
                query = query.strip()
                if query_notes:
                    query = f"{query}: {query_notes}"
                remind_md = cab.get_file_as_array('remind.md', 'notes')
                remind_md.append(
                    f"[{query_time_token}]{'' if is_recurring else 'd'} {query}")
                cab.write_file("remind.md", "notes",
                               '\n'.join(remind_md), is_quiet=True)
                log_msg(
                    f"""Scheduled "{query.strip()}" for {query_time_formatted}""", print_msg=True)
        return

    if len(response) > 0:
        if response == 'r':
            report_query()
        elif not response.startswith('n'):
            # send 'right now' reminder
            send_email(query.strip(), query_notes, False, is_quiet=True)


def manual_reminder(manual_message='', manual_date='', noconfirm=False):
    """
    Creates a reminder with a message and a date.
    If manual_message and/or manual_date are not provided,
        prompts the user to input them. 

    Args:
        manual_message (str): Optional. The reminder message.
        manual_date (str): Optional. The reminder date in a string format.

    Returns:
        None

    Example:
        manual_reminder('Buy groceries', '2023-04-03')
    """

    reminder_message = manual_message or input("What's the reminder?\n")
    reminder_date = manual_date or input(
        "\nWhen do you want to be reminded? (blank for now)\n") or "now"
    QUERY_TRACE.append(
        f"... calling parse_query({reminder_message},{reminder_date}) ")
    parse_query(manual_message=reminder_message,
                manual_date=reminder_date, noconfirm=noconfirm)


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
    parser.add_argument('-o', '--offset', nargs='?',
                        help=help_offset)
    parser.add_argument('-e', '--edit', action='store_true',
                        help='Edits remind.md through the terminal')
    parser.add_argument('--show-tomorrow', action='store_true',
                        help='Shows a list of reminders scheduled for tomorrow')
    parser.add_argument('manual_reminder_args', nargs='*')

    args = parser.parse_args()

    if args.list:
        list_reminders()
    elif args.generate:
        generate(force=args.force, dry_run=args.dry_run)
    elif args.later:
        mail_reminders_for_later()
    elif args.offset is not None:
        offset(args.offset.split(" "))
    elif args.edit:
        edit()
    elif args.show_tomorrow:
        show_tomorrow()
    elif args.manual_reminder_args:
        parse_query(query=' '.join(args.manual_reminder_args),
                    noconfirm=args.noconfirm)
    else:
        manual_reminder(manual_message=args.message or '',
                        manual_date=args.date or '', noconfirm=args.noconfirm)


if __name__ == '__main__':
    main()
