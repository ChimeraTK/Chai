from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Button,  Label, Static, Input, Button, ListView, ListItem, Input, DirectoryTree
from textual.message import Message

from textual import on

import deviceaccess as da

from chai.RegisterView import RegisterTree, DeviceStatus
from pathlib import Path
from typing import Iterable


class DeviceList(ListView):
    _devices: dict[str, str]

    def updateDmapFile(self, filename: str):
        self.clear()
        self._devices = self._parseDmapFile(filename)
        self.extend([ListItem(Label(name)) for name in self._devices.keys()])

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        dev_string: str = str(selected.item.children[0].renderable)
        self.app.query_one(DeviceView)._updateDeviceStatusLabel(
            DeviceStatus.Open, dev_string, self._devices[dev_string])
        self.app.query_one(RegisterTree).changeDevice(da.Device(dev_string))
        self.app.query_one("#btn_close_device").disabled = False
        self.app.query_one("#btn_close_device").label = "Close"

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
        with Horizontal(id="devices", classes="main_col"):
            with Vertical(classes="main_col"):
                yield DmapTree(".", id="dmap_tree")
                yield Label("dmap file path")
                yield Input(placeholder="./tests/KlmServer.dmap", id="field_map_file")
                yield Button("Load dmap file", id="Btn_load_boards")
            yield DeviceList()
        yield Label("No device loaded.", id="label_device_status")
        yield Button("Close", id="btn_close_device", disabled=True)

    @ on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        # dmap_file_path = self.query_one("#field_map_file").value
        dmap_file_path = "./tests/KlmServer.dmap"

        self.query_one(DeviceList).updateDmapFile(dmap_file_path)
        da.setDMapFilePath(dmap_file_path)

        self.app.SUB_TITLE = dmap_file_path
        self._updateDeviceStatusLabel(3)  # NoDeviceLoaded
        self.query_one("#btn_close_device").disabled = True
        self.query_one("#btn_close_device").label = "Close"

    @ on(Button.Pressed, "#btn_close_device")
    def _pressed_close_device(self) -> None:
        if (str(self.query_one("#btn_close_device").label) == "Close"):
            self._updateDeviceStatusLabel(DeviceStatus.Closed)
            self.app.query_one(RegisterTree)._changeDeviceStatus(DeviceStatus.Closed)
            self.query_one("#btn_close_device").label = "Open"
        else:  # Open
            self._updateDeviceStatusLabel(DeviceStatus.Open)
            self.app.query_one(RegisterTree)._changeDeviceStatus(DeviceStatus.Open)
            self.query_one("#btn_close_device").label = "Close"

    def _updateDeviceStatusLabel(self, status: DeviceStatus, name="", identifier=""):
        msg: str = str(self.query_one("#label_device_status").renderable)
        if status == DeviceStatus.Closed:
            msg.replace("Opened", "Closed")
        elif status == DeviceStatus.Open:
            if name == "":
                msg.replace("Closed", "Opened")
            else:
                msg = f"Opened {name} {identifier}"
        else:
            msg = "No device loaded."
        self.query_one("#label_device_status").update(msg)


class DmapTree(DirectoryTree):
    # TODO: See hidden folders default in options?
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if (path.is_dir() and not path.name.startswith(".") or path.suffix == ".dmap")]

    @on(DirectoryTree.FileSelected)
    def _file_selected(self, message: Message) -> None:
        self.app.query_one(DeviceList).updateDmapFile(str(message.path))
