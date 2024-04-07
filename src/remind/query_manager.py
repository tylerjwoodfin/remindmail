"""
handles reminder requests
"""

import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from remind.reminder import Reminder
from remind.reminder_manager import ReminderManager
from cabinet import Cabinet, Mail

class QueryManager:
    """
    handles reminder requests
    """

    def __init__(self, manager: ReminderManager) -> None:
        self.cabinet: Cabinet = manager.cabinet
        self.mail: Mail = manager.mail
        return

    def write_reminder_to_file(self, reminder: Reminder) -> None:
        """
        writes a reminder to remind.md
        """
        print("Not yet Implemented\n")
        print(reminder)

    def interpret_reminder_date(self, input_str: str) -> Reminder:
        """
        Parses a reminder date from a natural language string. 

        The function supports various date formats, including relative dates (e.g., "in 3 weeks"), 
        specific calendar dates (e.g., "July 4"), and weekdays (e.g., "Tuesday"). It interprets 
        these formats to return a Reminder object with the calculated date.

        Parameters:
        - input_str (str): The input string containing the date information.

        Returns:
        - Reminder: An object representing the reminder with the interpreted date.
        
        Raises:
        - ValueError: If the input string cannot be parsed into a known date format.
        """

        weekdays = {
            "monday": MO(+1), "mon": MO(+1),
            "tuesday": TU(+1), "tue": TU(+1),
            "wednesday": WE(+1), "wed": WE(+1),
            "thursday": TH(+1), "thu": TH(+1),
            "friday": FR(+1), "fri": FR(+1),
            "saturday": SA(+1), "sat": SA(+1),
            "sunday": SU(+1), "sun": SU(+1),
        }

        # Precompile regular expressions
        regex_patterns = {
            'relative': re.compile(r'(?:in )?(\d+) (day|week|month|year)s?(?: from now)?',
                                   re.IGNORECASE),
            'day_of_month': re.compile(r'\b(?:the )?(\d{1,2})(st|nd|rd|th)?\b', re.IGNORECASE),
            'every_weeks': re.compile(r'every (\d+) weeks?', re.IGNORECASE),
            'specific_date': re.compile((r'(?i)\b(january|february|march|april|may|june|july|august'
                                         r'|september|october|november|december)'
                                         r'(\d{1,2})(?:,? (\d{4}))?\b')),
            'mm_dd': re.compile(r'(\d{1,2})/(\d{1,2})'),
            'mm_dd_yyyy': re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})'),
            'yyyy_mm_dd': re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'),
            'every_n_days': re.compile(r'every (\d+) day?s?', re.IGNORECASE),
            'every_n_months': re.compile(r'every (\d+) month?s?', re.IGNORECASE),
            'every_n_dows': re.compile(r'every (\d+) (monday|mon|tuesday|tue|wednesday'
                                       r'|wed|thursday|thu|friday|fri|saturday|sat|sunday|sun)s?',
                                       re.IGNORECASE),
        }

        start_date = datetime.now() + timedelta(days=1)
        key, value, frequency, modifiers = '', '', None, 'd'

        # parse input_str
        if 'every' not in input_str:
            # relative
            if match := regex_patterns['relative'].search(input_str):
                number = int(match.group(1))
                unit = match.group(2)
                delta = {'day': relativedelta(days=number),
                         'week': relativedelta(weeks=number),
                         'month': relativedelta(months=number),
                         'year': relativedelta(years=number)}[unit]
                future_date = start_date + delta
                if future_date <= start_date:
                    raise ValueError((f"{future_date.strftime('%Y-%m-%d')}"
                                      " is in the past."))
                key, value = 'date', future_date.strftime('%Y-%m-%d')

            # mm/dd, mm/dd/yyyy
            elif match := regex_patterns['mm_dd'].match(input_str) or \
            regex_patterns['mm_dd_yyyy'].match(input_str):
                month, day = int(match.group(1)), int(match.group(2))
                year = int(match.group(3)) if match.lastindex == 3 else start_date.year
                proposed_date = datetime(year, month, day)
                # if the date is in the past, find the next occurrence
                if proposed_date <= start_date:
                    proposed_date = proposed_date + relativedelta(years=1)
                key, value = 'date', proposed_date.strftime('%Y-%m-%d')

            # yyyy-mm-dd
            elif match := regex_patterns['yyyy_mm_dd'].match(input_str):
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                proposed_date = datetime(year, month, day)
                if proposed_date <= start_date:
                    proposed_date = proposed_date + relativedelta(years=1)
                key, value = 'date', proposed_date.strftime('%Y-%m-%d')

            # day of month
            elif match := regex_patterns['day_of_month'].match(input_str):
                key, value = 'dom', match.group(1)

            # specific weekday
            elif any(day in input_str.lower() for day in weekdays):
                day_str = input_str.lower()
                for day, rel_day in weekdays.items():
                    if day in day_str:
                        next_weekday = start_date + relativedelta(weekday=rel_day)
                        key, value = 'date', next_weekday.strftime('%Y-%m-%d')
                        break

            # specific date
            elif match := regex_patterns['specific_date'].search(input_str):
                year = match.group(3) or start_date.year
                date_str = f"{year}-{match.group(1)[:3].title()}-{match.group(2).zfill(2)}"
                date_formatted = datetime.strptime(date_str, '%Y-%b-%d')
                # If the interpreted date is in the past, add a year to it
                if date_formatted <= start_date:
                    date_formatted = date_formatted + relativedelta(years=1)
                key, value = 'date', date_formatted.strftime('%Y-%m-%d')
        else:
            # 'every'
            modifiers = ''

            # every n days
            if match := regex_patterns['every_n_days'].match(input_str):
                key, frequency, modifiers = 'd', int(match.group(1)), ''

            # every n months
            elif match := regex_patterns['every_n_months'].match(input_str):
                key, frequency, modifiers = 'm', int(match.group(1)), ''

            # every n {dow}s (e.g., 'every 3 mondays')
            elif match := regex_patterns['every_n_dows'].match(input_str):
                dow = match.group(2).lower()
                if dow in weekdays:
                    key = 'dow'
                    value = dow
                    frequency = int(match.group(1))

            # every n weeks
            elif match := regex_patterns['every_weeks'].match(input_str):
                key, frequency, modifiers = 'w', int(match.group(1)), ''

        if not key:
            self.cabinet.log(f"Could not parse date: {input_str}",
                             level="warn", is_quiet=True)
            raise ValueError("Sorry, I didn't understand that.")

        return Reminder(key=key,
                        value=value,
                        frequency=frequency,
                        modifiers=modifiers,
                        title='',
                        notes='',
                        offset=0,
                        cabinet=self.cabinet,
                        mail=self.mail)

    def wizard_manual_reminder(self) -> Reminder:
        """
        Guides the user through the process of creating a new manual reminder
        by collecting necessary information
        through interactive prompts.

        Returns:
            Reminder: An instance of the Reminder class with
            properties populated based on user input.
        """

        def _format_input(text: str) -> str:
            return input(f"{text}?\n")

        title: str = _format_input("What's the reminder").strip()
        reminder_date_success: bool = False

        while not reminder_date_success:
            reminder_date: str = _format_input(
                "When do you want to be reminded").strip() or None

            try:
                reminder: Reminder = self.interpret_reminder_date(reminder_date)
                reminder.title = title
                reminder_date_success = True
            except ValueError as e:
                print(e)

        print(reminder)
        # self.write_reminder_to_file(reminder)

        return reminder
