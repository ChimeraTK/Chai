from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Tree, Input, Checkbox, Button, Input
from textual import on

from chai.DataView import RegisterValueField
from chai.ActionsView import ActionsView

from chai import Utils

import deviceaccess as da


class RegisterTree(Tree):

    _tree: Tree[dict] = Tree("Registers")
    _register_names = []

    def on_mount(self) -> None:
        self.watch(self.app, "is_open", lambda open: self.on_device_changed(open))
        self.watch(self.app, "registerInfo", lambda info: self.on_regster_info_changed(info))

    def on_device_changed(self, open: bool) -> None:
        self._tree.clear()
        if not open:
            return

        register_names = []
        for reg in self.app.currentDevice.getRegisterCatalogue():
            register_names.append(reg.getRegisterName())

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

        rc = self.app.currentDevice.getRegisterCatalogue()
        self.app.registerInfo = rc.getRegister(currentRegisterPath)

    def on_regster_info_changed(self, info: da.pb.RegisterInfo):
        if info is None:
            return
        dd = info.getDataDescriptor()
        if dd.rawDataType().getAsString() != "unknown" and dd.rawDataType().getAsString() != "none":
            # raw transfers are supported
            np_type = Utils.get_raw_numpy_type(dd.rawDataType())
            flags = [da.AccessMode.raw]
        else:
            # no raw transfer supported
            np_type = Utils.get_raw_numpy_type(dd.minimumDataType())
            flags = []

        if da.AccessMode.wait_for_new_data in info.getSupportedAccessModes():
            # we cannot use raw and wait_for_new_data at the same time
            self.app.currentDevice.activateAsyncRead()
            flags = [da.AccessMode.wait_for_new_data]

        if info.getDataDescriptor().fundamentalType() != da.FundamentalType.nodata:
            self.app.currentRegister = self.app.currentDevice.getTwoDRegisterAccessor(
                np_type, info.getRegisterName(), accessModeFlags=flags)
        else:
            self.app.currentRegister = self.app.currentDevice.getVoidRegisterAccessor(
                info.getRegisterName(), accessModeFlags=flags)


class RegisterView(Vertical):
    def compose(self) -> ComposeResult:
        yield Vertical(
            RegisterTree("Registers"),
            Vertical(
                Label("Find Module", classes="label"),
                Input(),
            ),
            Horizontal(
                Vertical(
                    Checkbox("Autoselect previous register"),
                    Button("Collapse all", id="btn_collapse"),
                ),
                Vertical(
                    Checkbox("Sort registers"),
                    Button("Expand all", id="btn_expand"),
                ),
            ),
            id="registers",
            classes="main_col")

    @on(Button.Pressed, "#btn_collapse")
    def _pressed_collapse(self) -> None:
        rt = self.query_one(RegisterTree)
        rt._tree.root.collapse_all()

    @on(Button.Pressed, "#btn_expand")
    def _pressed_expand(self) -> None:
        rt = self.query_one(RegisterTree)
        rt._tree.root.expand_all()
