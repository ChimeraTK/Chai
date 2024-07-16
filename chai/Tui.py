from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Button, Header, Label, Footer, Static, Placeholder, Tree, Input, Switch, Checkbox, Button, ListView, ListItem, TextArea, RadioSet, RadioButton, DataTable, OptionList, Input
from textual import events
from textual.reactive import reactive
from textual.message import Message
from textual.widgets.option_list import Option, Separator
from textual_plotext import PlotextPlot
import socket

from pprint import pp

import deviceaccess as da
import numpy as np


class PlotScreen(Screen):
    """Screen with a plot of current Register content."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield PlotextPlot()
        yield Footer()

    def on_mount(self) -> None:
        plt = self.query_one(PlotextPlot).plt
        y = plt.sin()
        plt.scatter(y)
        plt.title("Scatter Plot")  # to apply a title

    def on_key(self, event: events.Key) -> None:
        print(event.key)
        if event.name == "escape":
            self.app.pop_screen()


class RegisterValueField(Input):
    def on_input_changed(self, input):
        pass

    def write_data(self, currentRegister) -> None:
        if isinstance(currentRegister, da.ScalarRegisterAccessor):
            currentRegister.setAndWrite(currentRegister.getValueType()(self.value))


class RegisterTree(Tree):

    tree: Tree[dict] = Tree("Registers")

    def update_tree(self, register_names):
        self.tree.clear()
        for reg_name in register_names:
            split_name = reg_name.split('/')[1:]
            if len(split_name) > 1:
                node_added = False
                for child in self.tree.root.children:
                    if str(child.label) == split_name[0]:
                        if len(split_name) > 2:
                            parent_node = child.add(split_name[1])
                            parent_node.add_leaf(split_name[2])
                        else:
                            child.add_leaf(split_name[1])

                        node_added = True
                        break
                if not node_added:
                    new_node = self.tree.root.add(split_name[0])
                    new_node.add_leaf(split_name[1])
            else:
                self.tree.root.add_leaf(reg_name)

        self.recompose()

    def compose(self) -> ComposeResult:
        self.tree.root.expand()
        self.tree.show_root = False
        yield self.tree

    def on_tree_node_selected(self, selected):
        if not selected.node.is_root:
            currentRegisterPath = selected.node.label
            parent = selected.node.parent
            if not parent.is_root:
                currentRegisterPath = f"/{parent.label}/{currentRegisterPath}"
                self.post_message(self.Selected(currentRegisterPath))

    class Selected(Message):
        def __init__(self, currentRegister: str) -> None:
            self.currentRegister = currentRegister
            super().__init__()


ROWS = [
    ("Value", "Raw (dec)", "Raw (hex)"),
]

for i in range(10):
    x = ((i + 23) * 55) % 2234
    ROWS.append([x, x + 100, hex(x)])


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])


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


class DeviceColumn(Vertical):
    def compose(self) -> ComposeResult:
        yield Vertical(
            DeviceList(),
            Vertical(
                Label("Device status"),
                Vertical(
                    Static("No device loaded.", id="label_device_status"),
                    Button("Close", id="btn_close_device", disabled=True),
                ),
            ),
            Vertical(
                Label("Device properties"),
                Vertical(
                    Vertical(
                        Label("Device Name"),
                        Static("", id="field_device_name")
                    ),
                    Vertical(
                        Label("Device Identifier"),
                        Static("",  id="field_device_identifier")
                    ),
                    Vertical(
                        Label("dmap file path"),
                        Input(placeholder="./tests/KlmServer.dmap", id="field_map_file")
                    ),
                ),
            ),
            Button("Load dmap file", id="Btn_load_boards"),
            id="devices",
            classes="main_col")


class RegisterColumn(Vertical):
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


class PropertiesColumn(Vertical):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Register Path"),
            Static("/INT32_TEST/2DARRAY_MULTIPLEXED_RAW", id="label_register_path"),
            Horizontal(
                Vertical(
                    Label("Dimension"),
                    Static("1D", id="label_dimensions")
                ),
                Vertical(
                    Label("nElements"),
                    Static("12", id="label_nELements")
                ),
            ),
            Horizontal(
                Vertical(
                    Label("Data Type"),
                    Static("Signed Integer", id="label_data_type")
                ),
                Vertical(
                    Label("wait_for_new_data"),
                    Static("no", id="label_wait_for_new_data")
                ),
            ),
            Horizontal(
                Vertical(
                    Label("Numerical Address"),
                    Vertical(
                        Label("Bar"),
                        Static("2"),
                        Label("Address"),
                        Static("0"),
                        Label("Total size (bytes)"),
                        Static("48"),
                    ),
                ),
                Vertical(
                    Label("Fixed Point Interpretation"),
                    Vertical(
                        Label("Register width"),
                        Static("22"),
                        Label("Fractional bits"),
                        Static("0"),
                        Label("Signed Flag"),
                        Static("1"),
                    ),
                ),
            ),
            # DataTable(),
            RegisterValueField(),
            id="properties",
            classes="main_col")


class OptionsColumn(Vertical):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Options"),
            Vertical(
                Checkbox("Read after write", id="checkbox_read_after_write"),
                Button("Show plot", id="btn_show_plot")
            ),
            Label("Operations"),
            Vertical(
                Button("Read", disabled=True, id="btn_read"),
                Button("Write", disabled=True, id="btn_write"),
            ),
            Label("Continous Poll", id="label_ctn_pollread"),
            Vertical(
                Checkbox("enabled", id="checkbox_cont_pollread"),
                Label("Poll frequency", id="label_poll_update_frq"),
                RadioSet(
                    RadioButton("1 Hz", value=True),
                    RadioButton("100 Hz"),
                    disabled=True,
                    id="radio_set_freq"
                ),
                Label("Last poll time"),
                Static("2024-06-25T13:14:15.452"),
                Label("Avg. update interval"),
                Static(""),

            ),
            id="options",
            classes="main_col")


class ConsoleHardwareInterface(Container):

    def on_mount(self) -> None:
        # table = self.query_one(DataTable)
        # table.add_columns(*ROWS[0])
        # table.add_rows(ROWS[1:])
        pass

    def compose(self) -> ComposeResult:
        yield Horizontal(
            DeviceColumn(),
            RegisterColumn(),
            PropertiesColumn(),
            OptionsColumn()
        )


class MainScreen(Screen):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConsoleHardwareInterface()
        yield Footer()


class LayoutApp(App):

    currentDevice: da.Device = None
    currentRegister: da.GeneralRegisterAccessor = None
    dmap_file_path: str = None

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        rt = self.query_one(RegisterTree)
        if event.button.id == "btn_collapse":
            rt.tree.root.collapse_all()
        elif event.button.id == "btn_expand":
            rt.tree.root.expand_all()
        elif event.button.id == "Btn_load_boards":
            device_list = self.query_one(DeviceList)
            # dmap_file_path = self.query_one("#field_map_file").value
            self.dmap_file_path = "./tests/KlmServer.dmap"
            device_list.newList(self.getDevices(self.dmap_file_path))
            self.SUB_TITLE = self.dmap_file_path
            da.setDMapFilePath(self.dmap_file_path)
            self.currentDevice = da.Device("device")
            # self.currentDevice.open()
            self.query_one("#label_device_status").update("Device is open.")
            self.query_one("#btn_close_device").disabled = False
        elif event.button.id == "btn_close_device":
            self.currentDevice.close()
            self.query_one("#label_device_status").update("Device is closed.")
        elif event.button.id == "btn_read":
            self.read_and_update()
        elif event.button.id == "btn_write":
            self.write_value()
        elif event.button.id == "btn_show_plot":
            self.push_screen(PlotScreen())

    def write_value(self) -> None:
        self.query_one(RegisterValueField).write_data(self.currentRegister)
        if self.query_one("#checkbox_read_after_write").value:
            self.read_and_update()

    def getDevices(self, dmapPath: str):
        devices = []
        try:
            for line in open(dmapPath):
                if line and not line.startswith("@") and not line.startswith("#"):
                    device, path = line.split()
                    devices.append([device, path])
                    self.dmapPath = dmapPath
        except FileNotFoundError:
            self.notify(
                f"Could not open file: {dmapPath}",
                title="File not found",
                severity="warning",
            )
        return devices

    def on_register_tree_selected(self, message: RegisterTree.Selected) -> None:
        self.query_one("#label_register_path").update(message.currentRegister)
        rc = self.currentDevice.getRegisterCatalogue()
        reg_info = rc.getRegister(message.currentRegister)
        self.query_one("#label_nELements").update(str(reg_info.getNumberOfElements()))
        wait_for_new_data_label_text = "no"
        cont_polll_text = "Continous Poll"
        freq_text = "Poll frequency"

        if da.AccessMode.wait_for_new_data in reg_info.getSupportedAccessModes():
            wait_for_new_data_label_text = "yes"
            cont_polll_text = "Continous Read"
            freq_text = "Update frequency"

        self.query_one("#label_poll_update_frq").update(freq_text)
        self.query_one("#label_ctn_pollread").update(cont_polll_text)
        self.query_one("#label_wait_for_new_data").update(wait_for_new_data_label_text)

        if reg_info.getNumberOfDimensions() == 0:
            self.query_one("#label_dimensions").update("Scalar")
            self.currentRegister = self.currentDevice.getScalarRegisterAccessor(np.int32, message.currentRegister)
        elif reg_info.getNumberOfDimensions() == 1:
            self.query_one("#label_dimensions").update("1D")
            self.currentRegister = self.currentDevice.getOneDRegisterAccessor(np.int32, message.currentRegister)
        elif reg_info.getNumberOfDimensions() == 2:
            self.currentRegister = self.currentDevice.getTwoDRegisterAccessor(np.int32, message.currentRegister)
            self.query_one("#label_dimensions").update("2D")
        self.read_and_update()
        self.update_read_write_btn_status()
      # .def("isValid", &ChimeraTK::RegisterInfo::isValid)
      # .def("getRegisterName", DeviceAccessPython::RegisterInfo::getRegisterName)
      # .def("getNumberOfChannels", &ChimeraTK::RegisterInfo::getNumberOfChannels);

    def read_and_update(self) -> None:
        self.currentRegister.readLatest()
        rvf = self.query_one(RegisterValueField)
        rvf.clear()
        rvf.insert_text_at_cursor(str(self.currentRegister[0]))

    def update_read_write_btn_status(self):
        pollread = self.query_one("#checkbox_cont_pollread")
        if self.currentRegister:
            self.query_one("#btn_read").disabled = (pollread.value and self.currentRegister.isReadable())
            self.query_one("#btn_write").disabled = (pollread.value and self.currentRegister.isWriteable())

    def on_checkbox_changed(self, changed: Checkbox.Changed):
        if changed.control.id == "checkbox_cont_pollread":
            self.update_read_write_btn_status()
            self.query_one("#radio_set_freq").disabled = changed.control.value

    def on_device_list_selected(self, selected: DeviceList.Selected) -> None:
        dev_string: str = selected.selectedDevice
        self.query_one("#field_device_name").update(dev_string)
        self.query_one("#field_device_identifier").update(selected.selectedPath)
        reg_tree = self.query_one(RegisterTree)
        self.currentDevice = da.Device(dev_string)

        register_names = []
        for reg in self.currentDevice.getRegisterCatalogue():
            register_names.append(reg.getRegisterName())
        self.currentDevice.open()
        reg_tree.update_tree(register_names)

    def exit(self) -> None:
        print("closed")
        if self.currentDevice:
            self.currentDevice.close()
        super().exit()


if __name__ == "__main__":
    app = LayoutApp()
    app.run()
    app._on_shutdown_request
