from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MainApp import LayoutApp
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical, Container, Grid
from textual.widgets import Button, Label, Static, Input, Button, DataTable, Input
from textual.containers import ScrollableContainer
from textual.validation import Number
from textual.coordinate import Coordinate

from textual import on, events, log

from chai import Utils

import deviceaccess as da


class RegisterValueRow(Horizontal):

    channel = 0

    raw = Input()
    cooked = Input()
    hex = Input()
    raw = 0

    def __init__(self, raw):
        self.raw = raw
        super().__init__()

    def compose(self):
        yield Container(Input(placeholder=str(self.raw)))
        yield Container(Input())
        yield Container(Input())

    def update(self, raw_value):
        self.raw = raw_value
        self.recompose


class EditValueScreen(ModalScreen):
    table: DataTable
    first_submit: bool

    def __init__(self, owner, table: DataTable):
        super().__init__()
        self.table = table
        self.first_submit = True
        self._owner = owner

    def compose(self) -> ComposeResult:
        value = self.table.get_cell_at(self.table.cursor_coordinate)

        col = self.table.cursor_coordinate.column
        if col == 0:
            # cooked
            validPattern = r'^[0-9]*(\.[0-9]*)?$'
        elif col == 1:
            # raw decimal
            validPattern = r'^[0-9]*$'
        elif col == 2:
            # raw hex
            validPattern = r'^(0x)?[0-9a-fA-F]*$'
        else:
            raise RuntimeError("Selected column out of range")

        yield Grid(
            Label("Edit value", id="edit_value_dialog_title"),
            Input(value=str(value), placeholder="0", id="edit_value_dialog_input", validate_on=["changed"],
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
        self._owner.cellEditDone(self.query_one(Input).value)
        self.app.pop_screen()

    @on(Button.Pressed, "#edit_value_dialog_cancel")
    def pressed_cancel(self) -> None:
        self.app.pop_screen()


class RegisterValueField(ScrollableContainer):

    _channel: int = 0
    _isRaw: bool = False
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        table = DataTable()
        table.add_columns('Value', 'Raw (dec)', 'Raw (hex)')
        yield table

    def on_mount(self):
        self.watch(self.app, "currentRegister", lambda accessor: self.on_register_changed(accessor))

        self.watch(self.app, "register_value_changed", lambda x: self.update())

    def on_register_changed(self, accessor: da.TwoDRegisterAccessor):
        if accessor is None:
            return
        self._isRaw = da.AccessMode.raw in accessor.getAccessModeFlags()
        accessor.readLatest()
        self._channel = 0
        self.update()

    def changeChannel(self, channel: int):
        if self.app.currentRegister is None:
            return
        self._channel = channel
        self.update()

    def on_key(self, event: events.Key) -> None:
        if event.key != 'enter':
            return
        table = self.query_one(DataTable)
        if not table:
            return
        self.app.push_screen(EditValueScreen(self, table))

    def cellEditDone(self, value) -> None:
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row

        if not isinstance(self.app.currentRegister, da.TwoDRegisterAccessor):
            return

        if self._isRaw:

            if table.cursor_coordinate.column == 0:  # "Value" (cooked)
                self.app.currentRegister.setAsCooked(self._channel, row, value)
            elif table.cursor_coordinate.column == 1:  # "Raw (dec)"
                self.app.currentRegister[self._channel][row] = int(value)
            elif table.cursor_coordinate.column == 2:  # "Raw (hex)"
                self.app.currentRegister[self._channel][row] = int(value, 16)

            table.update_cell_at(
                coordinate=Coordinate(row, 0), value=self.app.currentRegister.getAsCooked(str, self._channel, row), update_width=True)
            table.update_cell_at(coordinate=Coordinate(row, 1), value=str(
                self.app.currentRegister[self._channel][row]), update_width=True)
            table.update_cell_at(coordinate=Coordinate(row, 2), value=hex(
                self.app.currentRegister[self._channel][row]), update_width=True)

        else:
            self.app.currentRegister[self._channel][row] = int(value)
            table.update_cell_at(coordinate=Coordinate(row, 0), value=str(
                self.app.currentRegister[self._channel][row]), update_width=True)

    def update(self) -> None:
        table = self.query_one(DataTable)
        table.clear(True)

        if not isinstance(self.app.currentRegister, da.TwoDRegisterAccessor):
            return

        if self._isRaw:
            table.add_columns('Value', 'Raw (dec)', 'Raw (hex)')
            for element, value in enumerate(self.app.currentRegister[self._channel]):
                table.add_row(
                    self.app.currentRegister.getAsCooked(
                        str,
                        self._channel,
                        element),
                    value,
                    hex(value),
                    label=str(element))
        else:
            table.add_columns('Value')
            for element, value in enumerate(self.app.currentRegister[self._channel]):
                table.add_row(value, label=str(element))


class RegisterInfo(Grid):
    _nChannels: int = 0

    def compose(self) -> ComposeResult:
        yield Label("Register Path", id="label_register_path")
        yield Static(" ", id="field_register_path")
        yield Label("Dimension")
        yield Static("", id="label_dimensions")
        yield Label("nElements")
        yield Static("", id="label_nELements")
        yield Label("nChannels")
        yield Static("", id="label_nChannels")
        yield Label("Data Type")
        yield Static("", id="label_data_type")
        yield Label("wait_for_new_data")
        yield Static("", id="label_wait_for_new_data")
        yield Label("Channel:")
        yield Input(value="0", placeholder="0", id="edit_value_dialog_input", type="integer")

    def on_mount(self):
        self.watch(self.app, "registerInfo", lambda info: self.on_regster_info_changed(info))

    def on_regster_info_changed(self, info: da.pb.RegisterInfo):
        if info is None:
            return
        self.query_one("#field_register_path", Static).update(info.getRegisterName())
        self.query_one("#label_nELements", Static).update(str(info.getNumberOfElements()))
        self.query_one("#label_nChannels", Static).update(str(info.getNumberOfChannels()))
        self._nChannels = info.getNumberOfChannels()

        dd = info.getDataDescriptor()
        self.query_one("#label_data_type", Static).update(Utils.build_data_type_string(dd))
        if info.getNumberOfDimensions() == 0:
            self.query_one("#label_dimensions", Static).update("Scalar")
        elif info.getNumberOfDimensions() == 1:
            self.query_one("#label_dimensions", Static).update("1D")
        elif info.getNumberOfDimensions() == 2:
            self.query_one("#label_dimensions", Static).update("2D")

    def on_input_submitted(self, change: Input.Submitted) -> None:
        if change.value.isdigit():
            value = int(change.value)
        else:
            # might be empty...
            value = 0
        if value >= self._nChannels:
            value = self._nChannels - 1
            change.input.value = str(value)
            self.notify("Channel out of range.", severity="warning")
        self.app.query_one(RegisterValueField).changeChannel(value)


class DataView(Vertical):

    def compose(self) -> ComposeResult:
        self.add_class("main_col")

        yield RegisterInfo(id="register_info")
        yield RegisterValueField(id="register_value_table")
