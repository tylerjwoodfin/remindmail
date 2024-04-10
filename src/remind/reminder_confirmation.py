"""
docstring
"""
from typing import List
from prompt_toolkit import Application, print_formatted_text, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import TextArea, Box, Label
from prompt_toolkit.layout.containers import WindowAlign, ConditionalContainer
from prompt_toolkit.filters import has_focus, Condition
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
        self.reminder.value = self.value_text_area.text
        self.reminder.frequency = int(self.frequency_text_area.text) \
            if self.frequency_text_area.text.isdigit() else 0
        self.reminder.notes = self.notes_input.text
        self.reminder.offset = int(self.offset_input_text_area.text) \
            if self.offset_input_text_area.text.isdigit() else 0

        print_formatted_text(HTML('<ansigreen>Saved.</ansigreen>'))
        self.application.exit()
        # save logic is handled in query manager

    def __init__(self, reminder: Reminder):

        self.reminder = reminder

        if not self.reminder.frequency:
            self.reminder.frequency = 0

        bindings = KeyBindings()

        # Key binding functions
        @bindings.add('down')
        @bindings.add('j')
        def _(event):
            event.app.layout.focus_next()
            self.update_toolbar_text()

        @bindings.add('up')
        @bindings.add('k')
        def _(event):
            event.app.layout.focus_previous()
            self.update_toolbar_text()

        # Initialize UI components
        self.reminder_types: List[ReminderKeyType] = \
            [screaming_snake_to_sentence_case(type.name) for type in ReminderKeyType]
        self.current_type_index = 0

        # save
        self.save_button = TextArea(text='Save',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansigreen bold blink')

        # title
        self.title_input = TextArea(text=reminder.title,
                                    multiline=False,
                                    prompt=HTML('<b><ansiblue>Title: </ansiblue></b>'))

        # type
        self.type_input = TextArea(text=self.reminder_types[self.current_type_index],
                                   read_only=True,
                                   multiline=False,
                                   prompt=HTML('<b><ansiblue>Type: </ansiblue></b>'))

        # value
        self.value_text_area = TextArea(text=self.reminder.value,
                                        multiline=False,
                                        prompt=HTML('<b><ansiblue>Value: </ansiblue></b>'))

        self.value_input = ConditionalContainer(
            content=self.value_text_area,
            filter=Condition(self.is_value_enabled)
        )

        # frequency
        self.frequency_text_area = TextArea(text=str(reminder.frequency),
                                            multiline=False,
                                            read_only=True,
                                            prompt=HTML('<b><ansiblue>Frequency: </ansiblue></b>'))

        self.frequency_input = ConditionalContainer(
            content=self.frequency_text_area,
            filter=Condition(self.is_frequency_enabled)
        )

        # offset
        self.offset_input_text_area = TextArea(text=str(reminder.offset),
                                     multiline=False,
                                     read_only=True,
                                     prompt=HTML('<b><ansiblue>Offset: </ansiblue></b>'))

        self.offset_input = ConditionalContainer(
            content=self.offset_input_text_area,
            filter=Condition(self.is_offset_enabled)
        )

        # modifiers
        self.modifiers_input_text_area = TextArea(text=str(reminder.modifiers),
                                        multiline=False,
                                        prompt=HTML('<b><ansiblue>Modifiers: </ansiblue></b>'))

        self.modifiers_input = ConditionalContainer(
            content=self.modifiers_input_text_area,
            filter=Condition(self.is_modifiers_enabled)
        )

        self.notes_input = TextArea(text=reminder.notes, multiline=True, prompt='Notes: ')

        # cancel
        self.cancel_button = TextArea(text='Cancel',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansired bold blink')
        self.status_bar = Box(
            body=Label(text=lambda: self.toolbar_text, align=WindowAlign.LEFT),
            style="reverse",
            height=1,
            padding_left=1,
            padding_right=0
        )

        # handle editing mode
        @bindings.add('v')
        def _(event):
            """
            Toggles between VI and EMACS mode

            Args:
                event (_type_): _description_
            """
            app = event.app
            if app.editing_mode == EditingMode.VI:
                app.editing_mode = EditingMode.EMACS
            else:
                app.editing_mode = EditingMode.VI

        # handle type
        @bindings.add('right', filter=has_focus(self.type_input))
        @bindings.add('l', filter=has_focus(self.type_input))
        def _(event):  # pylint: disable=unused-argument
            self.current_type_index = (self.current_type_index + 1) % len(self.reminder_types)
            self.type_input.text = self.reminder_types[self.current_type_index]

        @bindings.add('left', filter=has_focus(self.type_input))
        @bindings.add('h', filter=has_focus(self.type_input))
        def _(event):  # pylint: disable=unused-argument
            self.current_type_index = (self.current_type_index - 1) % len(self.reminder_types)
            self.type_input.text = self.reminder_types[self.current_type_index]

        # handle frequency
        @bindings.add('right', filter=has_focus(self.frequency_input))
        @bindings.add('l', filter=has_focus(self.frequency_input))
        def _(event):  # pylint: disable=unused-argument
            self.reminder.frequency += 1
            self.frequency_text_area = str(self.reminder.frequency)

        @bindings.add('left', filter=has_focus(self.frequency_input))
        @bindings.add('h', filter=has_focus(self.frequency_input))
        def _(event):  # pylint: disable=unused-argument
            if self.reminder.frequency > 0:
                self.reminder.frequency -= 1
                self.frequency_text_area = str(self.reminder.frequency)

        # handle offset
        @bindings.add('right', filter=has_focus(self.offset_input_text_area))
        @bindings.add('l', filter=has_focus(self.offset_input_text_area))
        def _(event):  # pylint: disable=unused-argument
            self.reminder.offset += 1
            self.offset_input_text_area.text = str(self.reminder.offset)

        @bindings.add('left', filter=has_focus(self.offset_input_text_area))
        @bindings.add('h', filter=has_focus(self.offset_input_text_area))
        def _(event):  # pylint: disable=unused-argument
            if self.reminder.offset > 0:
                self.reminder.offset -= 1
                self.offset_input_text_area.text = str(self.reminder.offset)

        # finalize component
        self.main_container = HSplit([
            self.title_input,
            self.type_input,
            self.value_input,
            self.frequency_input,
            self.offset_input,
            HSplit(children=[
                self.modifiers_input
            ], height=2),
            HSplit(children=[
                self.notes_input
            ], height=3, style="bg:ansiyellow"),
            Window(height=1),  # Separator space before buttons.
            HSplit([
                Window(width=1)
            ], align="left", padding=1),
            self.save_button,
            self.cancel_button,
            Window(height=1),  # Separator space before status bar.
            self.status_bar
        ], padding=0)

        layout = Layout(self.main_container)
        self.application = Application(layout=layout, key_bindings=bindings, full_screen=True)

        # save
        @bindings.add('enter', filter=has_focus(self.save_button))
        @bindings.add(' ', filter=has_focus(self.save_button))
        # pylint: disable=unused-argument
        def _(event):  # pylint: disable=unused-argument
            self.save_reminder()

        # cancel
        @bindings.add('enter', filter=has_focus(self.cancel_button))
        @bindings.add(' ', filter=has_focus(self.cancel_button))
        @bindings.add('q')
        def _(event): #pylint: disable=unused-argument
            self.application.exit()
            print("Canceled.")

    def update_toolbar_text(self) -> None:
        """
        Updates the toolbar text based on the currently focused input in the application.

        This function dynamically sets the toolbar text to provide contextual help or
        information related to the input field currently in focus. It constructs a
        frequency text string that varies based on the selected reminder type and its
        frequency, and then updates the toolbar text to reflect the current interaction context,
        such as editing the title, type, value, frequency, or modifiers of the reminder.
        """

        rtype = self.reminder_types[self.current_type_index].lower()

        frequency_text = f"{self.frequency_text_area} {rtype}s"
        if rtype == 'day of week':
            rtype = self.value_text_area.text
            frequency_text = f"{self.frequency_text_area} {rtype}s"

        # handle different verbiage based on frequency
        if self.frequency_text_area == "0":
            frequency_text = rtype
        elif self.frequency_text_area == "1":
            frequency_text = rtype

        if self.application.layout.has_focus(self.title_input):
            self.toolbar_text = "The title for your reminder"
        elif self.application.layout.has_focus(self.type_input):
            self.toolbar_text = f"Send every {frequency_text}"
        elif self.application.layout.has_focus(self.value_input):
            if rtype == 'day of week':
                self.toolbar_text = 'Enter a weekday ("sunday" through "saturday")'
            elif rtype == 'day of month':
                self.toolbar_text = 'Enter a number 1-31'
            elif rtype == 'date':
                self.toolbar_text = 'Enter a date (YYYY-MM-DD)'
        elif self.application.layout.has_focus(self.frequency_input):
            self.toolbar_text = \
                f"How often the reminder should occur (every {frequency_text})"
        elif self.application.layout.has_focus(self.offset_input_text_area):
            self.toolbar_text = f"How many {rtype}s to offset the current schedule"
        elif self.application.layout.has_focus(self.modifiers_input_text_area):
            self.toolbar_text = "d: delete after sending; c: execute as command instead of email"
        elif self.application.layout.has_focus(self.notes_input):
            self.toolbar_text = "Add notes to your reminder"
        elif self.application.layout.has_focus(self.save_button):
            self.toolbar_text = "Save your reminder"
        elif self.application.layout.has_focus(self.cancel_button):
            self.toolbar_text = "Cancel your reminder"

    def is_value_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text in ['Date', 'Day Of Week', 'Day Of Month']

    def is_frequency_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text not in ['Date', 'Later']

    def is_offset_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text not in ['Date', 'Later']

    def is_modifiers_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text not in ['Later']

    def run(self):
        """
        docstring
        """

        app = self.application
        app.layout.focus(self.save_button)
        self.update_toolbar_text()
        app.run()
