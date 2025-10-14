from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MainApp import LayoutApp
from chai.ExceptionDialog import ExceptionDialog
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
from chai.Utils import AccessorHolder
from numpy import dtype


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
            validPattern = r'^-?[0-9]*(\.[0-9]*)?$'
        elif col == 1:
            # raw decimal
            validPattern = r'^-?[0-9]*$'
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


class ContentTable(DataTable):

    async def _on_click(self, event: events.Click) -> None:
        await super()._on_click(event)
        if event.button == 1 and event.chain >= 2:
            self.app.push_screen(EditValueScreen(self.parent, self))


class RegisterValueField(ScrollableContainer):

    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        table = ContentTable()
        table.add_columns('Value', 'Raw (dec)', 'Raw (hex)')
        yield table

    def on_mount(self):
        self.watch(self.app, "registerValueChanged", lambda x: self.update())
        self.watch(self.app, "channel", lambda x: self.update())
        self.watch(self.app, "register", lambda x: self.update())

    def on_key(self, event: events.Key) -> None:
        if event.key != 'enter':
            return
        table = self.query_one(ContentTable)
        if not table:
            return
        self.app.push_screen(EditValueScreen(self, table))

    def currentlySelectedValue(self):
        table = self.query_one(ContentTable)
        if not table:
            return 0
        if table.cursor_coordinate is None:
            return 0
        if table.cursor_coordinate.row is None:
            return 0
        if table.cursor_coordinate.column is None:
            return 0
        try:
            return table.get_cell_at(table.cursor_coordinate)
        except Exception:
            return 0

    def cellEditDone(self, value) -> None:
        table = self.query_one(ContentTable)
        row = table.cursor_coordinate.row

        if self.app.register is None or not isinstance(self.app.register.accessor, da.TwoDRegisterAccessor):
            return

        if self.app._isRaw:  # was self._isRaw why not checking the app instead of having a local member?

            if table.cursor_coordinate.column == 0:  # "Value" (cooked)
                self.app.register.accessor.setAsCooked(self.app.channel, row, value)
            elif table.cursor_coordinate.column == 1:  # "Raw (dec)"
                self.app.register.accessor[self.app.channel][row] = int(value)
            elif table.cursor_coordinate.column == 2:  # "Raw (hex)"
                self.app.register.accessor[self.app.channel][row] = int(value, 16)

            table.update_cell_at(
                coordinate=Coordinate(row, 0), value=self.app.register.accessor.getAsCooked(
                    # str, # what is that string for?
                    self.app.channel, row), update_width=True)
            valueType: dtype = self.app.register.accessor.getValueType()
            table.update_cell_at(coordinate=Coordinate(row, 1), value=str(
                self.app.register.accessor[self.app.channel][row]), update_width=True)
            convertedHex = self.signed_to_unsigned_hex(
                self.app.register.accessor[self.app.channel][row], valueType.itemsize*8)
            table.update_cell_at(coordinate=Coordinate(row, 2), value=convertedHex, update_width=True)

        else:
            self.app.register.accessor[self.app.channel][row] = int(value)
            table.update_cell_at(coordinate=Coordinate(row, 0), value=str(
                self.app.register.accessor[self.app.channel][row]), update_width=True)

    def signed_to_unsigned_hex(self, value: int, bits=32) -> str:
        # Mask the value to the specified number of bits
        mask = (1 << bits) - 1
        unsigned_value = value & mask
        return hex(unsigned_value)

    def update(self) -> None:
        table = self.query_one(ContentTable)
        table.clear(True)

        if self.app.register is None:
            return

        if self.app.register.info.getDataDescriptor().fundamentalType() is da.FundamentalType.nodata:
            table.add_columns("No data")
            return

        if not isinstance(self.app.register.accessor, da.TwoDRegisterAccessor):
            return

        if self.app._isRaw:
            table.add_columns('Value', 'Raw (dec)', 'Raw (hex)')
            for element, value in enumerate(self.app.register.accessor[self.app.channel]):
                table.add_row(
                    self.app.register.accessor.getAsCooked(
                        # str, # where is that from?
                        self.app.channel,
                        element),
                    value,
                    hex(value),
                    label=str(element))
                log(f"Row {element}: cooked {self.app.register.accessor.getAsCooked(self.app.channel, element)}, raw {value} (0x{hex(value)})")
        else:
            table.add_columns('Value')
            for element, value in enumerate(self.app.register.accessor[self.app.channel]):
                table.add_row(value, label=str(element))


class RegisterInfo(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Register Path:", id="label_register_path", classes="right_align"),
            Static(" ", id="field_register_path"),
            Container(
                Label("Dimension:", classes="right_align"),
                Static("", classes="spacer"),
                Static("", id="label_dimensions", classes="left_align"),
                classes="centered_row",
            ),
            Container(
                Label("nElements:", classes="right_align"),
                Static("", classes="spacer"),
                Static("", id="label_nELements", classes="left_align"),
                classes="centered_row",
            ),
            Container(
                Label("nChannels:", classes="right_align"),
                Static("", classes="spacer"),
                Static("", id="label_nChannels", classes="left_align"),
                classes="centered_row",
            ),
            Container(
                Label("Data Type:", classes="right_align"),
                Static("", classes="spacer"),
                Static("", id="label_data_type", classes="left_align"),
                classes="centered_row",
            ),
            Container(
                Label("Access Mode:", classes="right_align"),
                Static("", classes="spacer"),
                Static("", id="label_wait_for_new_data", classes="left_align"),
                classes="centered_row",
            ),
            classes="info_box")

    def on_mount(self):
        self.watch(self.app, "register", lambda register: self.on_regster_info_changed(register))

    def on_regster_info_changed(self, register: AccessorHolder):
        if register is None:
            return
        info = register.info
        self.query_one("#field_register_path", Static).update(info.getRegisterName())
        self.query_one("#label_nELements", Static).update(str(info.getNumberOfElements()))
        self.query_one("#label_nChannels", Static).update(str(info.getNumberOfChannels()))
        # concatenate list of access modes to a comma separated string
        modeStringList = []
        modeList = info.getSupportedAccessModes()
        if da.AccessMode.wait_for_new_data in modeList:
            modeStringList.append("Wait for new data")
        if da.AccessMode.raw in modeList:
            modeStringList.append("RAW")

        self.query_one("#label_wait_for_new_data", Static).update(", ".join(modeStringList))
        dd = info.getDataDescriptor()
        self.query_one("#label_data_type", Static).update(Utils.build_data_type_string(dd))
        if info.getNumberOfDimensions() == 0:
            self.query_one("#label_dimensions", Static).update("Scalar")
        elif info.getNumberOfDimensions() == 1:
            self.query_one("#label_dimensions", Static).update("1D")
        elif info.getNumberOfDimensions() == 2:
            self.query_one("#label_dimensions", Static).update("2D")


class DataView(Vertical):

    def compose(self) -> ComposeResult:
        self.add_class("main_col")

        yield RegisterInfo(id="register_info")
        yield RegisterValueField(id="register_value_table")
