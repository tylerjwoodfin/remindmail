"""
The data structure for Reminders
"""

class Reminder:
    """
    A class representing a reminder.

    Attributes
    ----------
    message : str
        The message for the reminder.
    next_date : date
        The date of the next occurrence of the reminder
    notes : str, optional
        Additional notes for the reminder (default is an empty string).
    is_recurring : bool, optional
        Indicates whether the reminder is recurring (default is False).

    Methods
    -------
    message
        Getter and setter method for the message attribute.
    next_date
        Getter and setter method for the next_date attribute.
    notes
        Getter and setter method for the notes attribute.
    is_recurring
        Getter and setter method for the is_recurring attribute.
    """

    def __init__(self, message, next_date, notes='', is_recurring=False):
        """
        Initializes a new Reminder instance.

        Parameters
        ----------
        message : str
            The message for the reminder.
        next_date : str
            The date of the next occurrence of the reminder in the format 'YYYY-MM-DD'.
        notes : str, optional
            Additional notes for the reminder (default is an empty string).
        is_recurring : bool, optional
            Indicates whether the reminder is recurring (default is False).
        """
        self._message = message
        self._next_date = next_date
        self._notes = notes
        self._is_recurring = is_recurring

    @property
    def message(self):
        """Getter and setter method for the message attribute."""
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @property
    def next_date(self):
        """Getter and setter method for the next_date attribute."""
        return self._next_date

    @next_date.setter
    def next_date(self, value):
        self._next_date = value

    @property
    def notes(self):
        """Getter and setter method for the notes attribute."""
        return self._notes

    @notes.setter
    def notes(self, value):
        self._notes = value

    @property
    def is_recurring(self):
        """Getter and setter method for the is_recurring attribute."""
        return self._is_recurring

    @is_recurring.setter
    def is_recurring(self, value):
        self._is_recurring = value
