"""
docstring
"""
from typing import List
from prompt_toolkit import Application, print_formatted_text, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.widgets import TextArea, Button, Label
from prompt_toolkit.filters import has_focus
from remind.reminder import Reminder, ReminderKeyType, screaming_snake_to_sentence_case

class ReminderConfirmation:
    """
    docstring
    """

    def save_reminder(self):
        """
        docstring
        """
        # Update reminder instance with values from text areas
        self.reminder.title = self.title_input.text
        self.reminder.frequency = int(self.frequency_input.text) \
            if self.frequency_input.text.isdigit() else 0
        self.reminder.notes = self.notes_input.text
        self.reminder.offset = int(self.offset_input.text) \
            if self.offset_input.text.isdigit() else 0

        print_formatted_text(HTML('<ansigreen>Saved.</ansigreen>'))
        print("Reminder:")
        print(self.reminder)
        self.application.exit()

    def __init__(self, reminder: Reminder):
        self.reminder = reminder
        bindings = KeyBindings()

        # Key binding functions
        @bindings.add('down')
        def _(event):
            event.app.layout.focus_next()

        @bindings.add('up')
        def _(event):
            event.app.layout.focus_previous()

        @bindings.add('right')
        def _(event):  # pylint: disable=unused-argument
            self.current_type_index = (self.current_type_index + 1) % len(self.reminder_types)
            self.type_label.text = self.reminder_types[self.current_type_index]

        @bindings.add('left')
        def _(event):  # pylint: disable=unused-argument
            self.current_type_index = (self.current_type_index - 1) % len(self.reminder_types)
            self.type_label.text = self.reminder_types[self.current_type_index]

        # Initialize UI components
        self.reminder_types: List[ReminderKeyType] = \
            [screaming_snake_to_sentence_case(type.name) for type in ReminderKeyType]
        self.current_type_index = 0
        self.save_button = Button(text='Submit', handler=self.save_reminder)
        self.type_label = Label(text=self.reminder_types[self.current_type_index])
        self.title_input = TextArea(text=reminder.title, multiline=False, prompt='Title: ')
        self.frequency_input = TextArea(text=str(reminder.frequency),
                                        multiline=False,
                                        prompt='Frequency: ')
        self.notes_input = TextArea(text=reminder.notes, multiline=True, prompt='Notes: ')
        self.offset_input = TextArea(text=str(reminder.offset), multiline=False, prompt='Offset: ')

        # Arranging containers
        container = HSplit([
            # Directly including save_button in the layout
            self.save_button,
            # Other form fields
            self.type_label,
            self.title_input,
            self.frequency_input,
            self.notes_input,
            self.offset_input,
        ])

        layout = Layout(container)
        self.application = Application(layout=layout, key_bindings=bindings, full_screen=True)

        # Bind 'enter' and 'space' to save reminder when focus is on the save button
        @bindings.add('enter', filter=has_focus(self.save_button))
        @bindings.add(' ', filter=has_focus(self.save_button))
        # pylint: disable=unused-argument
        def save_event_handler(event):
            print("OK")
            self.save_reminder()

    def run(self):
        """
        docstring
        """
        self.application.run()
