"""
The main class
"""

import os
import re
from enum import Enum
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from .remindmail_utils import RemindMailUtils

class GenerateType(Enum):
    """
    The options available for the `generate` function

    EMAIL will send each matching reminder
    LIST will print each matching reminder to the console
    """
    EMAIL = 'email'
    LIST = 'list'

class RemindMail:
    """
    Contains the logic for parsing, generating, and sending reminders
    """

    def log_msg(self, message, level="info", path=None, print_msg=False):
        """A wrapper for cab.log to handle the remindmail log setting"""

        path_log = RemindMailUtils.cab.get("path", "log")
        path = path or path_log
        path = f"{path}/{str(datetime.today().strftime('%Y-%m-%d'))}"

        RemindMailUtils.query_trace.append(message)

        if print_msg:
            print(message)

        RemindMailUtils.cab.log(f"remindmail: {message}", level=level, file_path=path,
                                is_quiet=level == "info")

    def generate(self, force: bool = False, dry_run: bool = False,
                 generate_date: int = None, generate_type: GenerateType = GenerateType.EMAIL):
        """
        Mails reminders from the remind.md file in {PATH_LOCAL}.
        Intended to be run from crontab (try 'remindmail generate force' to run immediately)
        """

        if generate_date is None:
            generate_date = datetime.today()

        today_index = generate_date.day

        day_of_month_reminders_generated = RemindMailUtils.cab.get(
            "remindmail", "day_generated")

        if day_of_month_reminders_generated == '':
            day_of_month_reminders_generated = 0

        # do not generate more than once in one day unless `remind generate force`
        if not (today_index != day_of_month_reminders_generated
                and generate_date.hour > 3) and not force and not dry_run:
            RemindMail().log_msg(
                "Reminders have already been generated in the past 12 hours.", level="debug")
            return

        RemindMail().log_msg("Generating reminders")

        command = ''

        current_time = RemindMailUtils().get_user_time()
        epoch_day = int(current_time/60/60/24)
        epoch_week = int(current_time/60/60/24/7)
        epoch_month = int(generate_date.month)

        remindmd_file = RemindMailUtils.cab.get_file_as_array(
            "remind.md", "notes") or []

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
                        RemindMail().log_msg(
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
                    split_type in ['sun', 'mon', 'tue',
                                   'wed', 'thu', 'fri', 'sat']
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
                    if generate_type == GenerateType.EMAIL and not dry_run:
                        RemindMailUtils().send_email(item.split(' ', 1)[1],
                                                item_notes, "remind.md")
                    if dry_run and generate_type == GenerateType.EMAIL:
                        RemindMail().log_msg(
                            f"Test Mode. Not Sending: {item.split(' ', 1)[1]}", level="debug")
                    elif generate_type == GenerateType.LIST:
                        print(item)
                if token_after == 1:
                    RemindMail().log_msg(
                        f"Deleting item from remind.md: {item}")
                    if not dry_run:
                        try:
                            remindmd_file.remove(_item)
                        except ValueError as err:
                            RemindMail().log_msg(
                                f"Could not remove from remind.md: {err}", level="error")
                    elif generate_type != GenerateType.LIST:
                        RemindMail().log_msg(f"(Test Mode. Not deleting {item})",
                                             level="debug")
                elif token_after > 1:
                    remindmd_file[index] = (item.replace(
                        f"]{token_after} ", f"]{token_after-1} "))

                if is_command:
                    if not dry_run:
                        print("Executing command:\n", command)
                        os.system(command)
                    else:
                        RemindMail().log_msg(f"Test Mode. Not executing {item})",
                                             level="debug")

        RemindMailUtils.cab.write_file("remind.md", "notes",
                                       '\n'.join(remindmd_file), is_quiet=True)

        if not dry_run:
            RemindMail().log_msg(
                f"Setting remindmail -> day_generated to {today_index}")
            RemindMailUtils.cab.put("remindmail", "day_generated", today_index)
        elif generate_type != GenerateType.LIST:
            RemindMail().log_msg(
                f"Test Mode. Not setting cabinet -> remindmail -> day_generated to {today_index}",
                level="debug"
            )

        RemindMail().log_msg("Generated tasks")

    def show_tomorrow(self):
        """
        Prints reminders from remind.md tagged with tomorow's date in YYYY-MM-DD format
        """

        tomorrow = datetime.today() + timedelta(days=1)
        RemindMail().generate(force=True, dry_run=True, generate_date=tomorrow,
                              generate_type=GenerateType.LIST)

    def parse_query(self, query=None, manual_message='', manual_date='', noconfirm=False):
        """
        Parses arguments to determine what to email or what to write to a file for later.

        Args:
            query (str): The query string to parse (default: None).
            manual_message (str): The manual message to use if query is None (default: '').
            manual_date (str): The manual date to use (default: '').
            noconfirm (bool, optional): If True, bypass the confirmation screen.
        """

        today = str(datetime.today().strftime('%Y-%m-%d'))
        weekdays = ['sunday', 'monday', 'tuesday',
                    'wednesday', 'thursday', 'friday', 'saturday']

        # helper functions
        def get_larger(string_a, string_b):
            """A helper function to return the larger string between string_a and string_b"""

            return string_a if len(string_a) > len(string_b) else string_b

        def strip_to(query):
            """A helper function to remove the portion after 'to' or 'day to'"""
            if query.startswith(' to ') or query.startswith('to ') or query.startswith('day to '):
                return ''.join(query.split('to')[1:]).strip()

            return query.strip()

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

        if query is None:
            query = manual_message

        query_original = query
        RemindMailUtils.query_trace.append(query)
        query_time_token = ''  # the 'meat' between [] in remind.md
        query_notes = ''
        query_time_formatted = ''
        query_notes_formatted = ''
        is_recurring = False

        def report_query():
            print("Reporting bad query via email...")
            RemindMail().log_msg(
                f"RemindMail query reported: {query_original}", level="warn")
            RemindMailUtils().send_email(f"Bad Query: {today}", '<br>'.join(
                RemindMailUtils.query_trace).replace("\n", "<br>"), False, is_quiet=False)

        if manual_date == 'now':
            manual_date = today

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
                                "every day"] + [f"every {day}" for day in weekdays]

        is_recurring = any(re.findall(
            '|'.join(is_recurring_options), query, flags=re.IGNORECASE))

        if is_recurring:
            for weekday in weekdays:
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
        _days = re.findall("in [0-9]+ days|in 1 day",
                           query, flags=re.IGNORECASE)
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
            day_prefixes = [f"on {day[:3]}" for day in weekdays] + \
                [f"next {day[:3]}" for day in weekdays]
            for day in day_prefixes:
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

            if not query_time_formatted and manual_date != today:
                query_time_format = '%A, %B %d'

                if parsed_date[0].year != datetime.today().year:
                    query_time_format = '%A, %B %d, %Y'

                query_time_formatted = parsed_date[0].strftime(
                    query_time_format)

            if manual_message:
                query = manual_message
            else:
                if len(parsed_date[1]) > 1:
                    _join_operator = ''
                    if len(parsed_date[1]) > 1:
                        _join_operator = parsed_date[1][1]
                    query = ''.join(get_larger(
                        parsed_date[1][0], _join_operator))
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
                RemindMailUtils.query_trace.append(prompt)

                response = input(prompt)
                RemindMailUtils.query_trace.append(response)
            else:
                response = 'y'

            if response == 'p':
                query_time_token = ''
                query_time_formatted = ''
                query = query_original
                print("\n------------------------------")
                RemindMailUtils.query_trace.append(
                    "\n------------------------------")

            elif response == 'l':
                query_time_token = 'any'
                is_recurring = True
                query_time_formatted = 'later'

            elif response == 'm':
                print("\n\n")
                RemindMail().manual_reminder()
                return

            elif response == 't':
                days = ["Monday", "Tuesday", "Wednesday",
                        "Thursday", "Friday", "Saturday", "Sunday"]
                weekday = days[(datetime.now() + timedelta(days=1)).weekday()]
                RemindMail().manual_reminder(query, weekday)
                return

        # send immediate reminders
        if query_time_formatted == 'right now' and response == 'y':
            RemindMailUtils().send_email(query.strip(), query_notes, False, is_quiet=True)
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
                    remind_md = RemindMailUtils.cab.get_file_as_array(
                        'remind.md', 'notes')
                    remind_md.append(
                        f"[{query_time_token}]{'' if is_recurring else 'd'} {query}")
                    RemindMailUtils.cab.write_file("remind.md", "notes",
                                                   '\n'.join(remind_md), is_quiet=True)
                    RemindMail().log_msg(
                        f"Scheduled \"{query.strip()}\" for {query_time_formatted}",
                        print_msg=True
                    )
            return

        if len(response) > 0:
            if response == 'r':
                report_query()
            elif not response.startswith('n'):
                # send 'right now' reminder
                RemindMailUtils().send_email(query.strip(), query_notes, is_quiet=True)

    def manual_reminder(self, manual_message='', manual_date='', noconfirm=False):
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
        RemindMailUtils.query_trace.append(
            f"... calling parse_query({reminder_message},{reminder_date}) ")
        RemindMail().parse_query(manual_message=reminder_message,
                                 manual_date=reminder_date, noconfirm=noconfirm)
