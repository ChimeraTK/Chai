from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Horizontal, Vertical, Container, Center, Middle, Grid
from textual.widgets import Button, Header, Label, Footer, Static, Tree, Input, Checkbox, Button, ListView, ListItem, RadioSet, RadioButton, DataTable, Input
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable
from textual import events, on
from textual.validation import Validator, ValidationResult, Regex

import deviceaccess as da


class RegisterTree(Tree):

    tree: Tree[dict] = Tree("Registers")
    register_names = []

    def update_tree(self, register_names):
        self.register_names = register_names
        self.tree.clear()
        for reg_name in register_names:
            split_name = reg_name.split('/')[1:]
            current_level = self.tree.root
            while len(split_name) > 1:
                node_added = False
                for child in current_level.children:
                    if str(child.label) == split_name[0]:
                        current_level = child
                        node_added = True
                        break
                if not node_added:
                    current_level = current_level.add(split_name[0])
                split_name = split_name[1:]

            current_level.add_leaf(split_name[0])
        self.recompose()

    def compose(self) -> ComposeResult:
        self.tree.root.expand()
        self.tree.show_root = False
        yield self.tree

    def on_tree_node_selected(self, selected):
        if not selected.node.is_root:
            currentRegisterPath = selected.node.label
            parent = selected.node.parent
            while not parent.is_root:
                currentRegisterPath = f"/{parent.label}/{currentRegisterPath}"
                parent = parent.parent
            if currentRegisterPath in self.register_names:
                self.post_message(self.Selected(currentRegisterPath))

    class Selected(Message):
        def __init__(self, currentRegister: str) -> None:
            self.currentRegister = currentRegister
            super().__init__()


class DeviceList(ListView):

    pathes = {}

    class Selected(Message):

        def __init__(self, devicelist, li: ListItem) -> None:
            self.selectedDevice = str(li.children[0].renderable)
            self.selectedPath = devicelist.pathes[self.selectedDevice]
            super().__init__()

    def newList(self, deviceList):
        self.clear()
        for device, path in deviceList:
            self.append(ListItem(Label(device)))
            self.pathes[device] = path

    def on_list_view_selected(self, _lv, selected: ListItem):
        self.post_message(self.Selected())


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

    register: da.NumpyGeneralRegisterAccessor | None = None
    refreshrate: reactive[float] = reactive(1.0)
    channel: int = 0

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.update_timer = self.set_interval(self.refreshrate, self.read_and_update, pause=True)

    def on_key(self, event: events.Key) -> None:
        if event.key != 'enter':
            return
        table = self.query_one(DataTable)
        if not table:
            return
        self.app.push_screen(EditValueScreen(table, self.register, self.channel))

    def read_and_update(self) -> None:
        self.remove_children()

        self.register.readLatest()
        table = DataTable()
        table.add_columns('Value', 'Raw (dec)', 'Raw (hex)')
        self.mount(table)

        for element, value in enumerate(self.register[self.channel]):
            table.add_row(self.register.getAsCooked(str, self.channel, element), value, hex(value), label=str(element))

    def watch_refreshrate(self, refreshrate) -> None:
        self.update_timer = self.set_interval(refreshrate, self.read_and_update, pause=True)

    def write_data(self) -> None:
        self.register.write()
