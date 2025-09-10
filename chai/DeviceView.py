from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Static, Input, Button, ListView, ListItem, Input

from textual import on
from textual import log

import deviceaccess as da

from chai.RegisterView import RegisterTree

import os
import sys


class DeviceList(ListView):

    _devices: dict[str, str] = {}

    def updateDmapFile(self, filename: str):
        self.clear()
        if filename is None:
            return
        self._devices = self._parseDmapFile(filename)
        if self._devices != {}:
            self.extend([ListItem(Label(name)) for name in self._devices.keys()])
            da.setDMapFilePath(filename)

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        self.app.is_open = False
        self.app.device_alias = str(selected.item.children[0].content)
        self.app.device_cdd = self._devices[self.app.device_alias]
        self.app.is_open = True

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

    def on_mount(self) -> None:
        self.watch(self.app, "dmap_file_path", lambda path: self.updateDmapFile(path))


class DeviceView(Vertical):

    def compose(self) -> ComposeResult:
        yield Vertical(
            DeviceList(),
            Vertical(
                Label("Device status"),
                Vertical(
                    Label("No device loaded.", id="label_device_status"),
                    Button("Open", id="btn_open_close_device", disabled=True),
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

        self.watch(self.app, "device_alias", lambda alias: self.query_one(
            "#field_device_name").update(alias or "No device loaded."))

        self.watch(self.app, "device_cdd", lambda cdd: self.query_one(
            "#field_device_identifier").update(cdd or ""))

        def change_is_open(open: bool) -> None:
            self.query_one("#label_device_status").update("Device is "+("open" if open else "closed"))
            self.query_one("#btn_open_close_device").label = "Close" if open else "Open"
            self.query_one("#btn_open_close_device").disabled = self.app.device_alias is None
        self.watch(self.app, "is_open", change_is_open)

    @on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        self.app.dmap_file_path = self.query_one("#field_map_file").value

    @on(Button.Pressed, "#btn_open_close_device")
    def _pressed_open_close_device(self) -> None:
        self.app.is_open = not self.app.is_open
