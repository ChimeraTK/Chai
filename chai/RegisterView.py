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
    _currentDevice: da.Device | None = None

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

        self.app.query_one("#label_register_path").update(currentRegisterPath)
        rc = self._currentDevice.getRegisterCatalogue()
        reg_info = rc.getRegister(currentRegisterPath)
        self.app.query_one("#label_nELements").update(str(reg_info.getNumberOfElements()))
        wait_for_new_data_label_text = "no"
        cont_polll_text = "Continous Poll"
        freq_text = "Poll frequency"

        if da.AccessMode.wait_for_new_data in reg_info.getSupportedAccessModes():
            wait_for_new_data_label_text = "yes"
            cont_polll_text = "Continous Read"
            freq_text = "Update frequency"

        self.app.query_one("#label_poll_update_frq").update(freq_text)
        self.app.query_one("#label_ctn_pollread").update(cont_polll_text)
        self.app.query_one("#label_wait_for_new_data").update(wait_for_new_data_label_text)
        reginfo = self._currentDevice.getRegisterCatalogue().getRegister(
            currentRegisterPath)
        dd = reginfo.getDataDescriptor()

        if dd.rawDataType().getAsString() != "unknown" and dd.rawDataType().getAsString() != "none" :
            # raw transfers are supported
            np_type = Utils.get_raw_numpy_type(dd.rawDataType())
            flags = [da.AccessMode.raw]
        else :
            # no raw transfer supported
            np_type = Utils.get_raw_numpy_type(dd.minimumDataType())
            flags = []

        if da.AccessMode.wait_for_new_data in reginfo.getSupportedAccessModes() :
            # we cannot use raw and wait_for_new_data at the same time
            self._currentDevice.activateAsyncRead()
            flags = [da.AccessMode.wait_for_new_data]

        self.app.query_one("#label_data_type").update(Utils.build_data_type_string(dd))
        if reg_info.getNumberOfDimensions() == 0:
            self.app.query_one("#label_dimensions").update("Scalar")
        elif reg_info.getNumberOfDimensions() == 1:
            self.app.query_one("#label_dimensions").update("1D")
        elif reg_info.getNumberOfDimensions() == 2:
            self.app.query_one("#label_dimensions").update("2D")

        register = self._currentDevice.getTwoDRegisterAccessor(np_type, currentRegisterPath, accessModeFlags=flags)
        self.app.query_one(RegisterValueField).changeRegister(register)
        self.app.query_one(ActionsView).changeRegister(register)



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
                    Button("Collapse all",  id="btn_collapse"),
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