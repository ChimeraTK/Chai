from textual.app import  ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, Container, Grid
from textual.widgets import Button, Label, Static, Input, Button, DataTable, Input
from textual.containers import ScrollableContainer

from textual import on, events

import deviceaccess as da


class RegisterValueRow(Horizontal):

    channel = 0
    offset = 0

    raw = Input()
    cooked = Input()
    hex = Input()
    raw = 0

    def __init__(self, raw):
        self.raw = raw
        super().__init__()

    def compose(self):
        yield Container(Input(placeholder=self.raw))
        yield Container(Input())
        yield Container(Input())

    def update(self, raw_value):
        self.raw = raw_value
        self.recompose

class EditValueScreen(ModalScreen):
    table: DataTable
    first_submit: bool
    register: da.TwoDRegisterAccessor
    channel: int

    def __init__(self, table: DataTable, register: da.TwoDRegisterAccessor, channel: int):
        super().__init__()
        self.table = table
        self.first_submit = True
        self.register = register
        self.channel = channel

    def compose(self) -> ComposeResult:
        value = self.table.get_cell_at(self.table.cursor_coordinate)

        col = self.table.cursor_coordinate.column
        if col == 0:
            # cooked
            validPattern = r'^[0-9]*(\.[0-9]*)?$'
        elif col == 1 :
            # raw decimal
            validPattern = r'^[0-9]*$'
        elif col == 2:
            # raw hex
            validPattern = r'^(0x)?[0-9a-fA-F]*$'
        else:
            raise RuntimeError("Selected column out of range")

        yield Grid(
            Label("Edit value", id="edit_value_dialog_title"),
            Input(value=str(value), placeholder="0", id="edit_value_dialog_input", validate_on='changed',
                  restrict=validPattern),
            Button("Ok", variant="primary", id="edit_value_dialog_ok"),
            Button("Cancel", id="edit_value_dialog_cancel"),
            id="edit_value_dialog",
        )

    @on(Input.Submitted, "#edit_value_dialog_input")
    def on_submit(self) -> None:
        # Somehow the input submits once when the dialog is shown, so we need to ignore the first submit event
        if self.first_submit:
            self.first_submit = False
            return
        self.pressed_ok()

    @on(Button.Pressed, "#edit_value_dialog_ok")
    def pressed_ok(self) -> None:
        input = self.query_one(Input)
        row = self.table.cursor_coordinate.row
        if self.table.cursor_coordinate.column == 0:  # "Value" (cooked)
            self.register.setAsCooked(self.channel, row, input.value)
        elif self.table.cursor_coordinate.column == 1:  # "Raw (dec)"
            self.register[self.channel][row] = int(input.value)
        elif self.table.cursor_coordinate.column == 2:  # "Raw (hex)"
            self.register[self.channel][row] = int(input.value, 16)
        self.table.update_cell_at(
            coordinate=[row,0], value=self.register.getAsCooked(str, self.channel, row), update_width=True)
        self.table.update_cell_at(coordinate=[row,1], value=str(self.register[self.channel][row]), update_width=True)
        self.table.update_cell_at(coordinate=[row,2], value=hex(self.register[self.channel][row]), update_width=True)
        self.app.pop_screen()

    @on(Button.Pressed, "#edit_value_dialog_cancel")
    def pressed_cancel(self) -> None:
        self.app.pop_screen()

class RegisterValueField(ScrollableContainer):

    _register: da.NumpyGeneralRegisterAccessor | None = None
    _channel: int = 0

    def changeRegister(self, register: da.TwoDRegisterAccessor):
        self._register = register
        self._register.readLatest()
        self.update()


    def on_key(self, event: events.Key) -> None:
        if event.key != 'enter':
            return
        table = self.query_one(DataTable)
        if not table:
            return
        self.app.push_screen(EditValueScreen(table, self._register, self._channel))

    def update(self) -> None:
        self.remove_children()

        table = DataTable()
        table.add_columns('Value', 'Raw (dec)', 'Raw (hex)')
        self.mount(table)

        for element, value in enumerate(self._register[self._channel]):
            table.add_row(self._register.getAsCooked(str, self._channel, element), value, hex(value), label=str(element))


class DataView(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Register Path"),
            Static("", id="label_register_path"),
            Horizontal(
                Vertical(
                    Label("Dimension"),
                    Static("", id="label_dimensions")
                ),
                Vertical(
                    Label("nElements"),
                    Static("", id="label_nELements")
                ),
            ),
            Horizontal(
                Vertical(
                    Label("Data Type"),
                    Static("", id="label_data_type")
                ),
                Vertical(
                    Label("wait_for_new_data"),
                    Static("", id="label_wait_for_new_data")
                ),
            ),
            RegisterValueField(),
            id="properties",
            classes="main_col")
