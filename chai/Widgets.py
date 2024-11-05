from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Button, Header, Label, Footer, Static, Tree, Input, Checkbox, Button, ListView, ListItem, RadioSet, RadioButton, DataTable, Input
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.reactive import reactive

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


class RegisterValueField(ScrollableContainer):

    register: da.NumpyGeneralRegisterAccessor | None = None
    counter: int = 0
    refreshrate: reactive[float] = reactive(1.0)

    rows = []  # [RegisterValueRow(register)]

    def compose(self):
        for row in self.rows:
            yield row

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.update_timer = self.set_interval(self.refreshrate, self.read_and_update, pause=True)

    def read_and_update(self) -> None:
        self.rows = []
        if self.register is not None:
            self.register.readLatest()
            for value in self.register:
                rvr = RegisterValueRow(str(value))
                self.mount(rvr)
                rvr.scroll_visible()
        #self.recompose()

    def watch_refreshrate(self, refreshrate) -> None:
        self.update_timer = self.set_interval(refreshrate, self.read_and_update, pause=True)

    def on_input_changed(self, input):
        pass

    def write_data(self, currentRegister) -> None:
        if isinstance(currentRegister, da.ScalarRegisterAccessor):
            currentRegister.setAndWrite(currentRegister.getValueType()(self.value))
