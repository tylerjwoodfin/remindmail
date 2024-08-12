"""
The confirmation before saving a reminder through the manual reminder wizard
"""
import datetime
import textwrap
from typing import List
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit import Application, print_formatted_text, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import TextArea, Box, Label
from prompt_toolkit.layout.containers import WindowAlign, ConditionalContainer
from prompt_toolkit.filters import has_focus, Condition
from remind.reminder import Reminder, ReminderKeyType

class ReminderConfirmation:
    """
    The confirmation before saving a reminder through the manual reminder wizard
    """

    def save_reminder(self):
        """
        Saves the reminder by updating its attributes based on
            the user inputs from the UI components.

        This function captures values from various text areas
        within the interface and updates the corresponding attributes
        of the reminder instance. It handles type conversions and validations,
        ensuring that numerical values such as frequency and offset are
        properly set even if the input is non-numeric or empty. The function concludes
        by providing a visual confirmation to the user, indicating whether the
        reminder was saved or immediately sent, based on its type.
        It also exits the confirmation.
        """

        # update reminder instance with values from text areas
        self.reminder.title = self.title_text_area.text
        # self.reminder.key is saved dynamically
        self.reminder.value = self.value_text_area.text
        self.reminder.frequency = int(self.frequency_text_area.text) \
            if self.frequency_text_area.text.isdigit() else 0
        self.reminder.notes = self.notes_text_area.text
        self.reminder.offset = int(self.offset_input_text_area.text) \
            if self.offset_input_text_area.text.isdigit() else 0

        confirmation_text = "Saved"
        if self.reminder.key == ReminderKeyType.NOW:
            confirmation_text = "Sent"

        print_formatted_text(HTML(f'<ansigreen><b>{confirmation_text}.</b></ansigreen>'))
        self.application.exit(result="cancel")
        # save logic is handled in query manager

    def __init__(self, reminder: Reminder):
        self.reminder: Reminder = reminder
        self.toolbar_text: str = ""
        self.is_vi_mode: bool = False
        self.key_value_cache: dict = {}
        self.default_frequency()
        self.bindings = KeyBindings()
        self.initialize_ui_components()
        self.setup_key_bindings()
        self.main_container = self.build_main_container()
        self.application = Application(layout=Layout(self.main_container),
                                       key_bindings=self.bindings, full_screen=True)

    def default_frequency(self):
        """
        Sets the default frequency of the reminder if it is not already specified.
        """

        if not self.reminder.frequency:
            self.reminder.frequency = 0

    def setup_key_bindings(self):
        """
        Configures key bindings for the user interface.

        Establishes the keyboard interactions required for
        navigating through the confirmation,
        adjusting reminder properties, and handling save and cancel operations.
        It leverages defined handler
        functions to manage user inputs and actions efficiently, enhancing
        the confirmation's responsiveness
        and usability.
        """
        self.setup_key_handlers()
        self.setup_adjustable_property_handlers()
        self.setup_save_and_cancel_handlers()

    def initialize_ui_components(self):
        """
        Initializes and configures the UI components for the confirmation interface.
        
        This method sets up various text areas, buttons, and containers necessary for the user 
        to interact with and manage reminders. It leverages a mixture of conditional containers 
        and static text areas to provide a dynamic and responsive user experience. Each component 
        is configured to display specific attributes of a reminder and may be read-only or editable 
        based on the context.
        """

        def generate_textarea(text: str | None, prompt: str,
                            read_only: bool = False) -> TextArea:
            """
            Creates a configured TextArea widget for user input or display,
            wrapping long single-line input.

            Args:
                text (str | None): The initial text to display in the TextArea.
                    If None, an empty string is used.
                prompt (str): A label shown as a prompt in the TextArea.
                read_only (bool, optional): Specifies if the TextArea should
                    be read-only. Defaults to False.

            Returns:
                TextArea: The configured TextArea widget.
            """

            initial_text: str = text or ""
            wrapped_text: str = '\n'.join(textwrap.wrap(initial_text, replace_whitespace=False))

            text_area = TextArea(
                text=wrapped_text,
                multiline=True,
                read_only=read_only,
                prompt=HTML(f'<b><ansiblue>{prompt}: </ansiblue></b>'),
                height=Dimension(min=1, max=int(len(text or "")/40) + 1),
                wrap_lines=True
            )

            # Set cursor at the end of the text
            text_area.buffer.cursor_position = len(wrapped_text)

            return text_area

        self.reminder_types: List[ReminderKeyType] = list(ReminderKeyType)

        # text areas
        self.title_text_area = generate_textarea(self.reminder.title, 'Title')
        self.type_text_area = generate_textarea(self.reminder.key.label, 'Type', True)
        self.value_text_area = generate_textarea(self.reminder.value, 'Value', True)
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
        self.notes_text_area = TextArea(text=self.reminder.notes or "",
                                    multiline=True, prompt='Notes: ')

        # save
        self.save_button = TextArea(text='Save',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansigreen')

        # cancel
        self.cancel_button = TextArea(text='Cancel',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansired')

        # toolbar
        self.toolbar = Box(
            body=Label(text=lambda: self.toolbar_text, align=WindowAlign.LEFT),
            style="reverse",
            height=1,
            padding_left=1,
            padding_right=0
        )

    def build_main_container(self) -> HSplit:
        """
        Constructs and returns the main container for the confirmation interface.

        This method organizes all the UI components into a hierarchical
        structure using horizontal and vertical splits. Ensures that all
        elements are displayed correctly and function cohesively within
        the full-screen confirmation layout.

        Returns:
            HSplit: The root container that holds all other UI components,
            structured in a vertical layout.
        """
        return HSplit([
            self.title_text_area,
            self.type_text_area,
            self.value_input,
            self.frequency_input,
            self.offset_input,
            HSplit(children=[
                self.modifiers_input
            ], height=2),
            HSplit(children=[
                self.notes_text_area
            ], height=3,
                   style="bg:ansiyellow fg:ansiblack"),
            Window(height=1),  # button separator
            HSplit([
                Window(width=1)
            ], padding=1),
            self.save_button,
            self.cancel_button,
            Window(height=1),  # toolbar separator
            self.toolbar
        ], padding=0)

    def setup_key_handlers(self):
        """
        Configures key bindings for navigating through fields and adjusting reminder properties.
        """

        # custom helper functions, necessary because prompt_toolkit needs a function to bind to
        def _is_vi_mode_or_save():
            return self.is_vi_mode or self.application.layout.has_focus(self.save_button)

        def _is_vi_mode_and_type_input():
            return self.is_vi_mode and self.application.layout.has_focus(self.type_text_area)

        def _is_not_vi_mode():
            return not self.is_vi_mode

        def _is_vi_mode_and_text_area(text_area: TextArea):
            return self.is_vi_mode and self.application.layout.has_focus(text_area)

        def make_nav_handler(key):
            def nav_handler(event):
                self.handle_navigation(event, key)
            return nav_handler

        nav_keys: List[str] = ['up', 'down']
        nav_keys_vi_mode: List[str] = ['j', 'k']

        # handle navigation keys
        for nav_key in nav_keys_vi_mode + nav_keys:
            handler = make_nav_handler(nav_key)
            if nav_key in nav_keys_vi_mode:
                self.bindings.add(nav_key, filter=Condition(_is_vi_mode_or_save))(handler)
            else:
                self.bindings.add(nav_key)(handler)

        # handle left and right arrow keys
        @self.bindings.add('right', filter=has_focus(self.type_text_area))
        def _(event: KeyPressEvent): # pylint: disable=unused-argument
            self.cycle_types(1)

        @self.bindings.add('left', filter=has_focus(self.type_text_area))
        def _(event: KeyPressEvent): # pylint: disable=unused-argument
            self.cycle_types(-1)

        # 'i' to exit vi mode
        @self.bindings.add('i', filter=Condition(_is_vi_mode_or_save))
        def _(event: KeyPressEvent): # pylint: disable=unused-argument
            self.is_vi_mode = False
            self.update_toolbar_text()

        # 'esc' to enter vi mode
        @self.bindings.add('escape', filter=Condition(_is_not_vi_mode))
        def _(event: KeyPressEvent): # pylint: disable=unused-argument
            self.is_vi_mode = True
            self.update_toolbar_text()

        # Handle other keys in vi mode
        @self.bindings.add('<any>', filter=Condition(_is_vi_mode_or_save))
        def block_other_keys(event: KeyPressEvent):  # pylint: disable=unused-argument
            # Optionally log or handle any blocked keys
            pass

        @self.bindings.add('l', filter=Condition(_is_vi_mode_and_type_input))
        def _(event: KeyPressEvent): # pylint: disable=unused-argument
            self.cycle_types(1)
            self.update_toolbar_text()

        @self.bindings.add('h', filter=Condition(_is_vi_mode_and_type_input))
        def _(event: KeyPressEvent): # pylint: disable=unused-argument
            self.cycle_types(-1)
            self.update_toolbar_text()

        text_areas: List[TextArea] = [
            self.title_text_area,
            self.modifiers_input_text_area,
            self.notes_text_area
        ]

        def create_vi_binding(text_area: TextArea):
            @self.bindings.add('l', filter=Condition(lambda: _is_vi_mode_and_text_area(text_area)))
            def _(event: KeyPressEvent): # pylint: disable=unused-argument
                text_area.buffer.cursor_position += 1

            @self.bindings.add('h', filter=Condition(lambda: _is_vi_mode_and_text_area(text_area)))
            def _(event: KeyPressEvent): # pylint: disable=unused-argument
                text_area.buffer.cursor_position -= 1

        for text_area in text_areas:
            create_vi_binding(text_area)

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
            days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday",
                            "Thursday", "Friday", "Saturday"]
            def handler(event): # pylint: disable=unused-argument
                current_value = getattr(self.reminder, property_attr)

                if self.reminder.key == ReminderKeyType.DAY_OF_WEEK:
                    # Find the current day index and increment or decrement
                    index = days_of_week.index(current_value)
                    new_index = (index + 1) % 7 if increment else (index - 1 + 7) % 7
                    new_value = days_of_week[new_index]
                elif self.reminder.key == ReminderKeyType.DATE:
                    # Handle date increment/decrement
                    current_date = datetime.datetime.strptime(current_value, '%Y-%m-%d').date()
                    delta = datetime.timedelta(days=1 if increment else -1)
                    new_value = current_date + delta
                    new_value = new_value.strftime('%Y-%m-%d')
                else:
                    # Handle numeric increments/decrements
                    current_value = int(current_value)
                    new_value = max(current_value + (1 if increment else -1), 0)

                setattr(self.reminder, property_attr, new_value)
                text_area.text = str(new_value)
                self.update_toolbar_text()

            return handler

        # Bind handlers for frequency, offset, and value

        # Frequency handlers
        self.bindings.add('right', filter=has_focus(self.frequency_input))(
            create_handler('frequency', self.frequency_text_area, True))
        self.bindings.add('l', filter=has_focus(self.frequency_input))(
            create_handler('frequency', self.frequency_text_area, True))
        self.bindings.add('left', filter=has_focus(self.frequency_input))(
            create_handler('frequency', self.frequency_text_area, False))
        self.bindings.add('h', filter=has_focus(self.frequency_input))(
            create_handler('frequency', self.frequency_text_area, False))

        # Offset handlers
        self.bindings.add('right', filter=has_focus(self.offset_input))(
            create_handler('offset', self.offset_input_text_area, True))
        self.bindings.add('l', filter=has_focus(self.offset_input))(
            create_handler('offset', self.offset_input_text_area, True))
        self.bindings.add('left', filter=has_focus(self.offset_input))(
            create_handler('offset', self.offset_input_text_area, False))
        self.bindings.add('h', filter=has_focus(self.offset_input))(
            create_handler('offset', self.offset_input_text_area, False))

        # Value handlers
        if self.reminder.key == ReminderKeyType.DATE or \
            self.reminder.key == ReminderKeyType.DAY_OF_MONTH:

            self.bindings.add('right', filter=has_focus(self.value_input))(
                create_handler('value', self.value_text_area, True))
            self.bindings.add('l', filter=has_focus(self.value_input))(
                create_handler('value', self.value_text_area, True))
            self.bindings.add('left', filter=has_focus(self.value_input))(
                create_handler('value', self.value_text_area, False))
            self.bindings.add('h', filter=has_focus(self.value_input))(
                create_handler('value', self.value_text_area, False))

    def setup_save_and_cancel_handlers(self):
        """
        Configures key bindings for save and cancel actions within the application.

        This method sets up handlers that trigger on specific key presses when focus is on the save
        or cancel buttons. It defines actions for saving changes, updating the interface, and 
        exiting the application. These handlers enhance user interaction by providing quick 
        keyboard shortcuts for common actions.
        """

        # custom helper functions to accommodate prompt_toolkit's Conditions
        def _is_vi_mode_or_save_button():
            return self.is_vi_mode or self.application.layout.has_focus(self.save_button)

        @self.bindings.add('enter', filter=has_focus(self.save_button))
        @self.bindings.add(' ', filter=has_focus(self.save_button))
        def _(event):  # pylint: disable=unused-argument
            self.save_reminder()
            self.update_toolbar_text()

        # cancel
        @self.bindings.add('enter', filter=has_focus(self.cancel_button))
        @self.bindings.add(' ', filter=has_focus(self.cancel_button))
        @self.bindings.add('q', filter=Condition(_is_vi_mode_or_save_button))
        def _(event): #pylint: disable=unused-argument
            print_formatted_text(HTML('<ansired><b>Cancelled.</b></ansired>'))
            self.reminder.modifiers = "x"
            self.application.exit()

    def cycle_types(self, direction) -> None:
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
            # handle the case where the current type is not found
            # (should not happen in normal circumstances)
            return

        # calculate the new index cyclically
        new_index: int = (current_index + direction) % len(self.reminder_types)

        # handle invalid values for dates - default to tomorrow
        if self.reminder_types[new_index] == ReminderKeyType.DATE:
            self.value_text_area.text = (datetime.datetime.now()
                                         + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            self.reminder.value = self.value_text_area.text

        # set cache
        self.key_value_cache[self.reminder.key.label] = self.value_text_area.text

        # update the reminder's type with the new type
        self.reminder.key = self.reminder_types[new_index]

        # update the type area with the new type label
        self.type_text_area.text = self.reminder.key.label

        self.update_toolbar_text()

        # get cache
        try:
            if self.key_value_cache[self.reminder.key.label]:
                self.value_text_area.text = self.key_value_cache[self.reminder.key.label]
                self.reminder.value = self.key_value_cache[self.reminder.key.label]
        except KeyError:
            # cache not set for this type
            if self.reminder.key == ReminderKeyType.DAY_OF_WEEK:
                self.value_text_area.text = "Sunday"
            elif self.reminder.key == ReminderKeyType.DAY_OF_MONTH:
                self.value_text_area.text = "1"

            self.reminder.value = self.value_text_area.text

    def handle_navigation(self, event, key: str) -> None:
        """
        Handles keyboard navigation within the confirmation's UI.

        This method manages the focus transitions between UI components based on arrow keys or
        'j' and 'k' inputs, mimicking VI-style navigation. It updates the toolbar text to reflect 
        the current mode or focused item.

        Args:
            event (any): The event object containing details like the app instance.
            key (str): The key pressed that triggers the navigation.
        """

        # handle VI mode
        if (key == 'j' or key == 'k') and self.application.layout.has_focus(self.save_button):
            self.is_vi_mode = True

        if (key == 'j' and self.is_vi_mode) or key == 'down':
            event.app.layout.focus_next()
            self.update_toolbar_text()
            return

        if (key == 'k' and self.is_vi_mode) or key == 'up':
            event.app.layout.focus_previous()
            self.update_toolbar_text()
            return

        # "release" the key if not handled
        event.handled = False

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

        value_text = f"{self.value_text_area.text}"
        if rtype == ReminderKeyType.DATE.label:
            try:
                # attempt to parse dow from the text
                date = datetime.datetime.strptime(value_text, "%Y-%m-%d")
                value_text = date.strftime("%A")
            except ValueError:
                # Set default text if parsing fails
                value_text = "Enter a Date (YYYY-MM-DD)"

        # handle different verbiage based on frequency
        if self.frequency_text_area.text == "0":
            frequency_text = rtype
        elif self.frequency_text_area.text == "1":
            frequency_text = rtype

        if self.application.layout.has_focus(self.title_text_area):
            self.toolbar_text = "The title for your reminder"
        elif self.application.layout.has_focus(self.type_text_area):
            if self.type_text_area.text == ReminderKeyType.DATE.label:
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
                self.toolbar_text = value_text
        elif self.application.layout.has_focus(self.frequency_input):
            self.toolbar_text = \
                f"How often the reminder should occur (every {frequency_text})"
        elif self.application.layout.has_focus(self.offset_input_text_area):
            self.toolbar_text = f"How many {rtype}s to offset the current schedule"
        elif self.application.layout.has_focus(self.modifiers_input_text_area):
            self.toolbar_text = "d: delete after sending; c: execute as command instead of email"
        elif self.application.layout.has_focus(self.notes_text_area):
            self.toolbar_text = "Add notes to your reminder"
        elif self.application.layout.has_focus(self.save_button):
            self.toolbar_text = "Save your reminder"
        elif self.application.layout.has_focus(self.cancel_button):
            self.toolbar_text = "Cancel your reminder"

        if self.is_vi_mode:
            self.toolbar_text = "(VI Mode) " + self.toolbar_text

    def is_value_enabled(self) -> bool:
        """
        Determines if the 'Value' field should be enabled based on the selected reminder type.

        Returns:
            bool: True if the reminder type requires a value, False otherwise.
        """

        return self.type_text_area.text in [ReminderKeyType.DAY_OF_WEEK.label,
                                        ReminderKeyType.DAY_OF_MONTH.label,
                                        ReminderKeyType.DATE.label]

    def is_frequency_enabled(self) -> bool:
        """
        Checks if the 'Frequency' field should be active for the current reminder type.

        Returns:
            bool: True if the frequency setting is applicable, False otherwise.
        """

        return self.type_text_area.text not in [ReminderKeyType.DATE.label,
                                            ReminderKeyType.LATER.label,
                                            ReminderKeyType.NOW.label]

    def is_offset_enabled(self) -> bool:
        """
        Determines if the 'Offset' field is applicable based on the reminder type.

        Returns:
            bool: True if offsets can be set for the type, False if not.
        """

        return self.type_text_area.text not in [ReminderKeyType.DATE.label,
                                            ReminderKeyType.LATER.label,
                                            ReminderKeyType.NOW.label]

    def is_modifiers_enabled(self) -> bool:
        """
        Evaluates whether modifier options should be available for the reminder type.

        Returns:
            bool: True if modifiers are applicable, False otherwise.
        """

        return self.type_text_area.text not in [ReminderKeyType.LATER.label,
                                            ReminderKeyType.NOW.label]

    def run(self):
        """
        Initiates and runs the confirmation, setting initial focus and starting the UI.

        This method focuses the save button, updates the toolbar text,
        and launches the confirmation UI.
        """

        app = self.application
        app.layout.focus(self.save_button)
        self.update_toolbar_text()
        app.run()
