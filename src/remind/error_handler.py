"""
Handles errors and data integrity issues
"""

import traceback
from typing import Callable
from functools import wraps
import sys
from datetime import datetime


class ErrorHandler:
    """
    Handles and tries to resolve errors
    """

    @staticmethod
    def exception_handler(func: Callable) -> Callable:
        """
        A decorator to handle exceptions raised by the function it wraps
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except FileNotFoundError as e:
                filename = getattr(e, "filename", "Unknown file")
                self.cabinet.log(
                    f"'{filename}' was not found in {func.__name__}.", level="error"
                )

                resolved = self.help_set_path_remindmd()
                if resolved:
                    return func(self, *args, **kwargs)
                else:
                    sys.exit()
            except PermissionError as e:
                print(f"Error: Permission denied when accessing the file '{e}'.")
            # pylint: disable=W0718
            except Exception as e:
                print(f"An unexpected error occurred while processing '{e}': {e}")
                traceback.print_exc()

        return wrapper

    @staticmethod
    def parse_mm_dd(date_str: str) -> tuple[int, int] | None:
        """
        Parse an annual ``MM-DD`` string into ``(month, day)``.

        Uses a leap year for validation so ``02-29`` is accepted.
        Returns ``None`` if the string is not a valid month/day.
        """
        parts = str(date_str).split("-")
        if len(parts) != 2:
            return None
        try:
            month, day = int(parts[0]), int(parts[1])
            # Leap year so February 29 is valid
            datetime(2024, month, day)
            return month, day
        except ValueError:
            return None

    def is_valid_date(self, date_str: str) -> bool:
        """
        Checks if a date string is valid.

        Accepts one-time ``YYYY-MM-DD`` and annual ``MM-DD`` formats
        (including ``02-29``).
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return self.parse_mm_dd(date_str) is not None
