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
from remind.reminder import Reminder, ReminderKeyType

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
        # self.reminder.key is saved dynamically
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
        self.toolbar_text = ""
        self.default_frequency()
        self.bindings = KeyBindings()
        self.initialize_ui_components()
        self.setup_key_bindings()
        self.main_container = self.build_main_container()
        self.application = Application(layout=Layout(self.main_container),
                                       key_bindings=self.bindings, full_screen=True)

    def default_frequency(self):
        """
        docstring
        """
        if not self.reminder.frequency:
            self.reminder.frequency = 0

    def setup_key_bindings(self):
        """_summary_
        """
        self.setup_navigation_handlers()
        self.setup_type_handlers()
        self.setup_adjustable_property_handlers()
        self.setup_save_and_cancel_handlers()

    def initialize_ui_components(self):
        """_summary_
        """

        def generate_textarea(text: str | None, prompt: str,
                              read_only: bool = False) -> TextArea:
            text_area = TextArea(text=text or "",
                            multiline=False,
                            read_only=read_only,
                            prompt=HTML(f'<b><ansiblue>{prompt}: </ansiblue></b>'))
            text_area.buffer.cursor_position = len(text or "")
            return text_area

        self.reminder_types: List[ReminderKeyType] = list(ReminderKeyType)

        # text areas
        self.title_input = generate_textarea(self.reminder.title, 'Title')
        self.type_input = generate_textarea(self.reminder.key.label, 'Type', True)
        self.value_text_area = generate_textarea(self.reminder.value, 'Value')
        self.frequency_text_area = generate_textarea(str(self.reminder.frequency),
                                                     'Frequency', True)
        self.offset_input_text_area = generate_textarea(str(self.reminder.offset), 'Offset', True)
        self.modifiers_input_text_area = generate_textarea(self.reminder.modifiers, 'Modifiers')

        self.value_input = ConditionalContainer(
            content=self.value_text_area,
            filter=Condition(self.is_value_enabled)
        )

        # frequency
        self.frequency_input = ConditionalContainer(
            content=self.frequency_text_area,
            filter=Condition(self.is_frequency_enabled)
        )

        self.offset_input = ConditionalContainer(
            content=self.offset_input_text_area,
            filter=Condition(self.is_offset_enabled)
        )

        # modifiers
        self.modifiers_input = ConditionalContainer(
            content=self.modifiers_input_text_area,
            filter=Condition(self.is_modifiers_enabled)
        )

        # notes
        self.notes_input = TextArea(text=self.reminder.notes or "",
                                    multiline=True, prompt='Notes: ')

        # save
        self.save_button = TextArea(text='Save',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansigreen bold blink')

        # cancel
        self.cancel_button = TextArea(text='Cancel',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansired bold blink')

        # toolbar
        self.toolbar = Box(
            body=Label(text=lambda: self.toolbar_text, align=WindowAlign.LEFT),
            style="reverse",
            height=1,
            padding_left=1,
            padding_right=0
        )

    def build_main_container(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return HSplit([
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
            Window(height=1),  # button separator
            HSplit([
                Window(width=1)
            ], padding=1),
            self.save_button,
            self.cancel_button,
            Window(height=1),  # toolbar separator
            self.toolbar
        ], padding=0)

    def setup_navigation_handlers(self):
        """_summary_
        """
        def make_nav_handler(key):
            def nav_handler(event):
                self.handle_navigation(event, key)
            return nav_handler

        for nav_key in ['j', 'k', 'down', 'up']:
            handler = make_nav_handler(nav_key)
            self.bindings.add(nav_key)(handler)

    def setup_type_handlers(self):
        """
        docstring
        """
        @self.bindings.add('right', filter=has_focus(self.type_input))
        @self.bindings.add('l', filter=has_focus(self.type_input))
        def _(event): # pylint: disable=unused-argument
            self.cycle_types(1)

        @self.bindings.add('left', filter=has_focus(self.type_input))
        @self.bindings.add('h', filter=has_focus(self.type_input))
        def _(event): # pylint: disable=unused-argument
            self.cycle_types(-1)

    def setup_adjustable_property_handlers(self):
        """
        Set up key bindings for adjusting properties of reminders such as frequency and offset.
        This function allows for the dynamic binding of
            keys to increment and decrement various properties.
        It uses lambda functions to handle changes in a generalized manner,
            ensuring that values do not go below zero and updating the corresponding UI elements.

        Parameters:
        - property_attr: The attribute of the reminder to be adjusted.
        - text_area: The TextArea widget that displays the value of the property.

        The bindings are set up for both increasing and decreasing the values with 'right', 'left',
        'l', and 'h' keys.
        """
        def create_handler(property_attr, text_area, increment=True):
            def handler(event): #pylint: disable=unused-argument
                current_value = getattr(self.reminder, property_attr)
                new_value = max(current_value + (1 if increment else -1), 0)
                setattr(self.reminder, property_attr, new_value)
                text_area.text = str(new_value)
                self.update_toolbar_text()
            return handler

        # Frequency handlers
        self.bindings.add('right',filter=has_focus(self.frequency_input))\
            (create_handler('frequency', self.frequency_text_area, True))
        self.bindings.add('l', filter=has_focus(self.frequency_input))\
            (create_handler('frequency', self.frequency_text_area, True))
        self.bindings.add('left', filter=has_focus(self.frequency_input))\
            (create_handler('frequency', self.frequency_text_area, False))
        self.bindings.add('h', filter=has_focus(self.frequency_input))\
            (create_handler('frequency', self.frequency_text_area, False))

        # Offset handlers
        self.bindings.add('right', filter=has_focus(self.offset_input))\
            (create_handler('offset', self.offset_input_text_area, True))
        self.bindings.add('l', filter=has_focus(self.offset_input))\
            (create_handler('offset', self.offset_input_text_area, True))
        self.bindings.add('left', filter=has_focus(self.offset_input))\
            (create_handler('offset', self.offset_input_text_area, False))
        self.bindings.add('h', filter=has_focus(self.offset_input))\
            (create_handler('offset', self.offset_input_text_area, False))

    def setup_save_and_cancel_handlers(self):
        """
        docstring
        """
        @self.bindings.add('enter', filter=has_focus(self.save_button))
        @self.bindings.add(' ', filter=has_focus(self.save_button))
        def _(event):  # pylint: disable=unused-argument
            self.save_reminder()
            self.update_toolbar_text()

        # cancel
        @self.bindings.add('enter', filter=has_focus(self.cancel_button))
        @self.bindings.add(' ', filter=has_focus(self.cancel_button))
        @self.bindings.add('q')
        def _(event): #pylint: disable=unused-argument
            self.application.exit()

    def cycle_types(self, direction):
        """
        Cycles through the reminder types in the specified direction and updates the type input.

        Args:
            direction (int): The direction to cycle through the reminder types.
            Positive for forward, negative for backward.
        """

        # Find current index based on current reminder type
        # Create a generator to find the index of the current reminder type
        index_generator = (
            i for i, t in enumerate(self.reminder_types)
            if t.db_value == self.reminder.key.db_value
        )

        # Use next to get the first index from the generator or return None if no match is found
        current_index = next(index_generator, None)

        if current_index is None:
            # Handle the case where the current type is not found
            # (should not happen in normal circumstances)
            return

        # Calculate the new index cyclically
        new_index = (current_index + direction) % len(self.reminder_types)

        # Update the reminder's type with the new type
        self.reminder.key = self.reminder_types[new_index]

        # Update the text area with the new type label
        self.type_input.text = self.reminder.key.label

        # Optionally update any related UI elements or data
        self.update_toolbar_text()

    def handle_navigation(self, event, key: str) -> None:
        """
        docstring

        Args:
            event (any): _description_
            key (str): _description_
        """
        is_save_first_focus = self.application.layout.has_focus(self.save_button)
        app = event.app

        if key == 'j' or key == 'down':
            event.app.layout.focus_next()
            self.update_toolbar_text()
        if key == 'k' or key == 'up':
            event.app.layout.focus_previous()
            self.update_toolbar_text()

        # enable VI
        if (key == 'j' or key == 'k') and is_save_first_focus:
            app.editing_mode = EditingMode.VI
            self.toolbar_text = f"(VI Mode) {self.toolbar_text}"

    def update_toolbar_text(self) -> None:
        """
        Updates the toolbar text based on the currently focused input in the application.

        This function dynamically sets the toolbar text to provide contextual help or
        information related to the input field currently in focus. It constructs a
        frequency text string that varies based on the selected reminder type and its
        frequency, and then updates the toolbar text to reflect the current interaction context,
        such as editing the title, type, value, frequency, or modifiers of the reminder.
        """

        rtype = self.reminder.key.label

        frequency_text = f"{self.frequency_text_area.text} {rtype}s"
        if rtype == ReminderKeyType.DAY_OF_WEEK.label:
            rtype = self.value_text_area.text
            frequency_text = f"{self.frequency_text_area.text} {rtype}s"

        if self.reminder.key == ReminderKeyType.DAY_OF_MONTH:
            frequency_text = f"{self.frequency_text_area.text} of the month"

        # handle different verbiage based on frequency
        if self.frequency_text_area.text == "0":
            frequency_text = rtype
        elif self.frequency_text_area.text == "1":
            frequency_text = rtype

        if self.application.layout.has_focus(self.title_input):
            self.toolbar_text = "The title for your reminder"
        elif self.application.layout.has_focus(self.type_input):
            if self.type_input.text == ReminderKeyType.DATE.label:
                self.toolbar_text = "Send on a specific date (YYYY-MM-DD)"
            elif self.reminder.key == ReminderKeyType.LATER:
                self.toolbar_text = 'Save for Later'
            elif self.reminder.key == ReminderKeyType.NOW:
                self.toolbar_text = 'Send immediately'
            else:
                self.toolbar_text = f"Send every {frequency_text}"
        elif self.application.layout.has_focus(self.value_input):
            if rtype == ReminderKeyType.DAY_OF_WEEK.label:
                self.toolbar_text = 'Enter a weekday ("sunday" through "saturday")'
            elif rtype == ReminderKeyType.DAY_OF_MONTH.label:
                self.toolbar_text = 'Enter a number 1-31'
            elif rtype == ReminderKeyType.DATE.label:
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

        return self.type_input.text in [ReminderKeyType.DAY_OF_WEEK.label,
                                        ReminderKeyType.DAY_OF_MONTH.label,
                                        ReminderKeyType.DATE.label]

    def is_frequency_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text not in [ReminderKeyType.DATE.label,
                                            ReminderKeyType.LATER.label]

    def is_offset_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text not in [ReminderKeyType.DATE.label,
                                            ReminderKeyType.LATER.label]

    def is_modifiers_enabled(self) -> bool:
        """
        docstring
        """

        return self.type_input.text not in [ReminderKeyType.LATER.label]

    def run(self):
        """
        docstring
        """

        app = self.application
        app.layout.focus(self.save_button)
        self.update_toolbar_text()
        app.run()
