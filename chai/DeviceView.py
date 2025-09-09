from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Static, Input, Button, ListView, ListItem, Input
from textual.message import Message

from textual import on
from textual import log

import deviceaccess as da

from chai.RegisterView import RegisterTree

import os
import sys


class DeviceList(ListView):
    _devices: dict[str, str]

    def updateDmapFile(self, filename: str):
        self.clear()
        self._devices = self._parseDmapFile(filename)
        self.extend([ListItem(Label(name)) for name in self._devices.keys()])

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        dev_string: str = str(selected.item.children[0].content)
        self.app.query_one(DeviceView).query_one("#field_device_name").content = dev_string
        self.app.query_one("#field_device_identifier").content = self._devices[dev_string]
        self.app.query_one(RegisterTree).changeDevice(da.Device(dev_string))

    def _parseDmapFile(self, dmapPath: str) -> dict[str, str]:
        devices = {}
        try:
            lineCounter = 0
            for line in open(dmapPath):
                lineCounter += 1

                # remove comments from line
                line_no_comment = line.split('#', maxsplit=1)[0].strip()
                # remove empty and comment lines as well as @ commands
                if line_no_comment == "" or line.startswith("@"):
                    continue

                # split remaining line at first space
                splitline = line.split(maxsplit=1)
                if len(splitline) != 2:
                    self.notify(f"Could not parse DMAP file {dmapPath}, parsing error in line {lineCounter}",
                                title="Parsing error",
                                severity="warning",
                                )
                    return {}

                alias_name, cdd = splitline
                devices[alias_name] = cdd
        except FileNotFoundError:
            self.notify(
                f"Could not open file: {dmapPath}",
                title="File not found",
                severity="warning",
            )
            return {}
        return devices


class DeviceView(Vertical):
    def compose(self) -> ComposeResult:
        yield Vertical(
            DeviceList(),
            Vertical(
                Label("Device status"),
                Vertical(
                    Label("No device loaded.", id="label_device_status"),
                    Button("Close", id="btn_close_device", disabled=True),
                ),
            ),
            Vertical(
                Label("Device properties"),
                Vertical(
                    Vertical(
                        Label("Device Name"),
                        Label("", id="field_device_name")
                    ),
                    Vertical(
                        Label("Device Identifier"),
                        Label("", id="field_device_identifier")
                    ),
                    Vertical(
                        Label("dmap file path"),
                        Input(placeholder="*.dmap", id="field_map_file")
                    ),
                ),
            ),
            Button("Load dmap file", id="Btn_load_boards"),
            id="devices",
            classes="main_col")

    def on_mount(self) -> None:
        if len(sys.argv) > 1:
            self.query_one("#field_map_file").value = sys.argv[1]
            self.query_one("#Btn_load_boards").press()

    @on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        dmap_file_path = self.query_one("#field_map_file").value

        self.query_one(DeviceList).updateDmapFile(dmap_file_path)
        da.setDMapFilePath(dmap_file_path)

        self.SUB_TITLE = dmap_file_path
        self.query_one("#label_device_status").update("Device is open.")
        self.query_one("#btn_close_device").disabled = False

    @on(Button.Pressed, "#btn_close_device")
    def _pressed_close_device(self) -> None:
        self.app.query_one(RegisterTree).changeDevice(None)
        self.query_one("#label_device_status").update("Device is closed.")
