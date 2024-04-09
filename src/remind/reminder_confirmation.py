"""
docstring
"""
from typing import List
from prompt_toolkit import Application, print_formatted_text, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import TextArea, Box, Label
from prompt_toolkit.layout.containers import WindowAlign
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
        self.application.exit()
        # save logic is handled in query manager

    def __init__(self, reminder: Reminder):
        self.reminder = reminder
        self.toolbar_text = "This is a toolbar"

        if not self.reminder.frequency:
            self.reminder.frequency = 0

        bindings = KeyBindings()

        # Key binding functions
        @bindings.add('down')
        @bindings.add('j')
        def _(event):
            event.app.layout.focus_next()

        @bindings.add('up')
        @bindings.add('k')
        def _(event):
            event.app.layout.focus_previous()

        # Initialize UI components
        self.reminder_types: List[ReminderKeyType] = \
            [screaming_snake_to_sentence_case(type.name) for type in ReminderKeyType]
        self.current_type_index = 0

        self.save_button = TextArea(text='Save',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansigreen bold blink')
        self.title_input = TextArea(text=reminder.title, multiline=False, style="fg:orange")
        self.type_input = TextArea(text=f"< {self.reminder_types[self.current_type_index]} >",
                                   read_only=True,
                                   multiline=False)
        self.value_input = TextArea(text=self.reminder.value,
                                   multiline=False,
                                   prompt='Value: ')
        self.frequency_input = TextArea(text=str(reminder.frequency),
                                        multiline=False,
                                        prompt='Frequency: ')
        self.offset_input = TextArea(text=str(reminder.offset), multiline=False, prompt='Offset: ')
        self.modifiers_input = TextArea(text=str(reminder.modifiers),
                                        multiline=False,
                                        prompt='Modifiers: ')
        self.notes_input = TextArea(text=reminder.notes, multiline=True, prompt='Notes: ')
        self.cancel_button = TextArea(text='Cancel',
                                    read_only=True,
                                    multiline=False,
                                    style='fg:ansired bold blink')

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
            self.type_input.text = f"< {self.reminder_types[self.current_type_index]} >"

        @bindings.add('left', filter=has_focus(self.type_input))
        @bindings.add('h', filter=has_focus(self.type_input))
        def _(event):  # pylint: disable=unused-argument
            self.current_type_index = (self.current_type_index - 1) % len(self.reminder_types)
            self.type_input.text = f"< {self.reminder_types[self.current_type_index]} >"

        # handle frequency
        @bindings.add('right', filter=has_focus(self.frequency_input))
        @bindings.add('l', filter=has_focus(self.frequency_input))
        def _(event):  # pylint: disable=unused-argument
            self.reminder.frequency += 1
            self.frequency_input.text = str(self.reminder.frequency)

        @bindings.add('left', filter=has_focus(self.frequency_input))
        @bindings.add('h', filter=has_focus(self.frequency_input))
        def _(event):  # pylint: disable=unused-argument
            if self.reminder.frequency > 0:
                self.reminder.frequency -= 1
                self.frequency_input.text = str(self.reminder.frequency)

        # handle offset
        @bindings.add('right', filter=has_focus(self.offset_input))
        @bindings.add('l', filter=has_focus(self.offset_input))
        def _(event):  # pylint: disable=unused-argument
            self.reminder.offset += 1
            self.offset_input.text = str(self.reminder.offset)

        @bindings.add('left', filter=has_focus(self.offset_input))
        @bindings.add('h', filter=has_focus(self.offset_input))
        def _(event):  # pylint: disable=unused-argument
            if self.reminder.offset > 0:
                self.reminder.offset -= 1
                self.offset_input.text = str(self.reminder.offset)

        container = HSplit([
            HSplit(children=[
                self.title_input,
            ], height=2),
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

            # Status Bar at the bottom
            Box(
                body=Label(text=lambda: self.toolbar_text, align=WindowAlign.LEFT),
                style="fg:black bg:white",
                height=1,
                padding_left=1,
                padding_right=0
            )
        ], padding=0)

        layout = Layout(container)
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

    def run(self):
        """
        displays the reminder confirmation
        """

        app = self.application
        app.layout.focus(self.save_button)
        app.run()
