from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Static, Input, Button, ListView, ListItem, Input
from textual.message import Message

from textual import on

import deviceaccess as da

from chai.RegisterView import RegisterTree


class DeviceList(ListView):
    _devices: dict[str, str]

    def updateDmapFile(self, filename: str):
        self.clear()
        self._devices = self._parseDmapFile(filename)
        self.extend([ListItem(Label(name)) for name in self._devices.keys()])

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        dev_string: str = str(selected.item.children[0].renderable)
        self.app.query_one("#field_device_name").update(dev_string)
        self.app.query_one("#field_device_identifier").update(self._devices[dev_string])
        self.app.query_one(RegisterTree).changeDevice(da.Device(dev_string))

    def _parseDmapFile(self, dmapPath: str) -> dict[str, str]:
        devices = {}
        try:
            for line in open(dmapPath):
                if line and not line.startswith("@") and not line.startswith("#"):
                    device, path = line.split()
                    devices[device] = path
        except FileNotFoundError:
            self.notify(
                f"Could not open file: {dmapPath}",
                title="File not found",
                severity="warning",
            )
        return devices


class DeviceView(Vertical):
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
                        Static("", id="field_device_identifier")
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

    @on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        # dmap_file_path = self.query_one("#field_map_file").value
        dmap_file_path = "./tests/KlmServer.dmap"

        self.query_one(DeviceList).updateDmapFile(dmap_file_path)
        da.setDMapFilePath(dmap_file_path)

        self.SUB_TITLE = dmap_file_path
        self.query_one("#label_device_status").update("Device is open.")
        self.query_one("#btn_close_device").disabled = False

    @on(Button.Pressed, "#btn_close_device")
    def _pressed_close_device(self) -> None:
        self.app.query_one(RegisterTree).changeDevice(None)
        self.query_one("#label_device_status").update("Device is closed.")
