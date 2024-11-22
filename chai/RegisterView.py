from enum import Enum

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Widget
from textual.widgets import Button, Label, Tree, Input, Checkbox, Button, Input
from textual import on

from chai.DataView import RegisterValueField
from chai.ActionsView import ActionsView
from chai.DataView import DataView
from chai.DataView import RegisterInfo

from chai import Utils

import deviceaccess as da


class DeviceStatus(Enum):
    Open = 1
    Closed = 2
    NoDeviceLoaded = 3


class RegisterTree(Tree):

    _tree: Tree[dict] = Tree("Registers")
    _register_names = []
    _currentDevice: da.Device | None = None

    def _changeDeviceStatus(self, status: DeviceStatus) -> None:
        if self._currentDevice is None:
            raise ValueError("No device loaded.")
        if status == DeviceStatus.Open:
            self._currentDevice.open()
        elif status == DeviceStatus.Closed:
            self._currentDevice.close()
        else:
            raise ValueError(f"Unknown status: {status}")

    def changeDevice(self, device: da.Device | None):
        self._tree.clear()

        if self._currentDevice is not None:
            self._currentDevice.close()

        self._currentDevice = device

        if device is None:
            return

        register_names = []
        for reg in self._currentDevice.getRegisterCatalogue():
            register_names.append(reg.getRegisterName())
        self._currentDevice.open()

        self._register_names = register_names
        for reg_name in register_names:
            split_name = reg_name.split('/')[1:]
            current_level = self._tree.root
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

    def compose(self) -> ComposeResult:
        self._tree.root.expand()
        self._tree.show_root = False
        yield self._tree

    def on_tree_node_selected(self, selected):
        if selected.node.is_root:
            return

        currentRegisterPath = selected.node.label
        parent = selected.node.parent
        while not parent.is_root:
            currentRegisterPath = f"/{parent.label}/{currentRegisterPath}"
            parent = parent.parent

        if currentRegisterPath not in self._register_names:
            return

        rc = self._currentDevice.getRegisterCatalogue()
        registerInfo = rc.getRegister(currentRegisterPath)

        self.app.query_one("RegisterInfo").changeRegister(registerInfo)

        dd = registerInfo.getDataDescriptor()
        if dd.rawDataType().getAsString() != "unknown" and dd.rawDataType().getAsString() != "none":
            # raw transfers are supported
            np_type = Utils.get_raw_numpy_type(dd.rawDataType())
            flags = [da.AccessMode.raw]
        else:
            # no raw transfer supported
            np_type = Utils.get_raw_numpy_type(dd.minimumDataType())
            flags = []

        if da.AccessMode.wait_for_new_data in registerInfo.getSupportedAccessModes():
            # we cannot use raw and wait_for_new_data at the same time
            self._currentDevice.activateAsyncRead()
            flags = [da.AccessMode.wait_for_new_data]

        register = self._currentDevice.getTwoDRegisterAccessor(np_type, currentRegisterPath, accessModeFlags=flags)
        self.app.query_one(RegisterValueField).changeRegister(register)
        self.app.query_one(ActionsView).changeRegister(register)


class RegisterView(Vertical):
    def compose(self) -> ComposeResult:
        yield RegisterSelection()
        yield RegisterInfo(id="register_info")
        yield DataView()
        yield ActionsView()

    @on(Button.Pressed, "#btn_collapse")
    def _pressed_collapse(self) -> None:
        rt = self.query_one(RegisterTree)
        rt._tree.root.collapse_all()

    @on(Button.Pressed, "#btn_expand")
    def _pressed_expand(self) -> None:
        rt = self.query_one(RegisterTree)
        rt._tree.root.expand_all()


class DeviceStatus(Enum):
    Open = 1
    Closed = 2


class RegisterSelection(Widget):
    def compose(self) -> ComposeResult:
        yield RegisterTree("Registers")
        yield Button("Expand all", id="btn_expand")
        yield Button("Collapse all",  id="btn_collapse")
        # TODO: Implement filtering:
        # yield Input(id="input_find_module", placeholder="Find module")
        # TODO: Implement autoselect previous register, what is this?
        # yield Checkbox("Autoselect previous register")
        # TODO: Implement sorting:
        # yield Checkbox("Sort registers")

        return super().compose()
