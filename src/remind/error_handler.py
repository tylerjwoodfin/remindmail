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
                filename = getattr(e, 'filename', 'Unknown file')
                self.cabinet.log(f"'{filename}' was not found in {func.__name__}.", level="error")

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

    def is_valid_date(self, date_str: str) -> bool:
        """
        Checks if a date string is valid
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
