from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Button, Header, Label, Footer, Static, Tree, Input, Checkbox, Button, ListView, ListItem, RadioSet, RadioButton, DataTable, Input
from textual.message import Message
from textual.containers import ScrollableContainer

import socket

from pprint import pp

import deviceaccess as da
import numpy as np

from .Plotting import PlotScreen
from .Widgets import RegisterTree, DeviceList, RegisterValueField


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


class PropertiesColumn(ScrollableContainer):
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
                    RadioButton("1 Hz", value=True, id="radio_1hz"),
                    RadioButton("100 Hz", id="radio_100hz"),
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
            rt: RegisterTree = self.query_one(RegisterTree)
            rt.update_tree([])
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
        dd = self.currentDevice.getRegisterCatalogue().getRegister(
            message.currentRegister).getDataDescriptor()
        raw_type = dd.rawDataType()
        np_type = self.get_raw_numpy_type(raw_type)
        self.query_one("#label_data_type").update(self.build_data_type_string(dd))
        if np_type == "unknown":
            # when can this happen?
            np_type = np.int32
        if np_type == "void":
            self.query_one("#label_dimensions").update("Void")
            self.currentRegister = self.currentDevice.getVoidRegisterAccessor(message.currentRegister)
        #elif np_type == None:
            # can that ever happen?
            #pass            
        elif reg_info.getNumberOfDimensions() == 0:
            self.query_one("#label_dimensions").update("Scalar")
            self.currentRegister = self.currentDevice.getScalarRegisterAccessor(np_type, message.currentRegister)
        elif reg_info.getNumberOfDimensions() == 1:
            self.query_one("#label_dimensions").update("1D")
            self.currentRegister = self.currentDevice.getOneDRegisterAccessor(np_type, message.currentRegister)
        elif reg_info.getNumberOfDimensions() == 2:
            self.currentRegister = self.currentDevice.getTwoDRegisterAccessor(np_type, message.currentRegister)
            self.query_one("#label_dimensions").update("2D")
        rvf = self.query_one(RegisterValueField)
        if self.currentRegister is not None:
            rvf.register = self.currentRegister
            rvf.read_and_update()
        self.update_read_write_btn_status()
      # .def("isValid", &ChimeraTK::RegisterInfo::isValid)
      # .def("getRegisterName", DeviceAccessPython::RegisterInfo::getRegisterName)
      # .def("getNumberOfChannels", &ChimeraTK::RegisterInfo::getNumberOfChannels);

    def on_radio_set_changed(self, changed: RadioSet.Changed) -> None:
        if changed.pressed.id == "radio_1hz":
            self.query_one(RegisterValueField).refreshrate = 1
        if changed.pressed.id == "radio_100hz":
            self.query_one(RegisterValueField).refreshrate = 1 / 100

    def get_raw_numpy_type(self, raw_type):
        conversion = {
            "none": None, "int8": np.int8, "uint8": np.uint8, "int16": np.int16,
            "uint16": np.uint16, "int32": np.int32, "uint32": np.uint32, "int64": np.int64,
            "uint64": np.uint64, "float32": np.float32, "float64": np.float64, "string": str,
            "Boolean": bool, "Void": "void", "unknown": "unknown"}
        return conversion[raw_type.getAsString()]

    def build_data_type_string(self, data_desriptor) -> str:
        type_string = str(data_desriptor.fundamentalType())
        if data_desriptor.fundamentalType() == da.FundamentalType.numeric:
            type_string = "unsigned"
            if data_desriptor.isSigned():
                type_string = "signed "
            if data_desriptor.isIntegral():
                type_string += " integer"
            else:
                type_string += " fractional"
        return type_string.title()

    def read_and_update(self) -> None:
        #self.currentRegister.readLatest()
        rvf = self.query_one(RegisterValueField)
        #rvf.read_and_update()

    def update_read_write_btn_status(self):
        pollread: Checkbox = self.query_one("#checkbox_cont_pollread")
        if self.currentRegister is not None:
            self.query_one("#btn_read").disabled = (pollread.value or not self.currentRegister.isReadable())
            self.query_one("#btn_write").disabled = (pollread.value or not self.currentRegister.isWriteable())
            if pollread.value:
                self.query_one(RegisterValueField).update_timer.resume()
            else:
                self.query_one(RegisterValueField).update_timer.pause()

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
