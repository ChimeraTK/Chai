from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MainApp import LayoutApp
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Label, Static, Input, Button, ListView, ListItem, Input, DirectoryTree

from textual import on
from textual import log

import deviceaccess as da

from chai.RegisterView import RegisterTree

import os
import sys
from collections.abc import Callable


class DeviceList(ListView):

    _devices: dict[str, str] = {}
    if TYPE_CHECKING:
        app: LayoutApp

    def updateDmapFile(self, filename: str):
        log(f"updateDmapFile  {filename}")
        self.clear()
        if filename is None:
            return
        self._devices = self._parseDmapFile(filename)
        if self._devices != {}:
            self.extend([ListItem(Label(name)) for name in self._devices.keys()])
            da.setDMapFilePath(filename)

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        itemLabel = selected.item.children[0]
        assert isinstance(itemLabel, Label)
        self.app.isOpen = False
        self.app.deviceAlias = str(itemLabel.content)
        self.app.deviceCdd = self._devices[self.app.deviceAlias]
        self.app.isOpen = True

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
        self.watch(self.app, "dmapFilePath", lambda path: self.updateDmapFile(path))


class DeviceProperties(Vertical):
    def compose(self) -> ComposeResult:
        yield Vertical(
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
            ),
            classes="main_col")

    def on_mount(self) -> None:
        self.watch(self.app, "deviceAlias", lambda alias: self.query_one(
            "#field_device_name", Label).update(alias or "No device loaded."))

        self.watch(self.app, "deviceCdd", lambda cdd: self.query_one(
            "#field_device_identifier", Label).update(cdd or ""))


class InputWithEnterAction(Input):
    action: Callable[[], None] = lambda: None

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop("action", None)
        super().__init__(*args, **kwargs)

    def _key_enter(self, key) -> None:
        if key.key == "enter":
            self.action()


class DmapView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Load dmap file from:"),
            InputWithEnterAction(id="field_root_dir", value=os.getcwd(),
                                 placeholder="Root directory", action=self._pressed_refresh_dir),
            DirectoryTree("./", id="directory_tree"),  # TODO: maybe add show non dmap, open on double click
            Label("or enter dmap file path:"),
            Input(placeholder="*.dmap", id="field_map_file"),
            Horizontal(
                Button("Load dmap file", id="Btn_load_boards"),
                Label("\n|"),
                Button("Reload tree", id="Btn_refresh_dir"),
            ),
            id="devices",
            classes="main_col")

    def on_mount(self) -> None:
        self.query_one("#directory_tree", DirectoryTree).guide_depth = 2
        self.query_one("#field_map_file", Input).value = sys.argv[1]
        if len(sys.argv) > 1:
            self.query_one("#Btn_load_boards", Button).press()

    @on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        self.app.dmapFilePath = self.query_one("#field_map_file", Input).value
        # switch view
        # TODO: if valid dmap path from terminal start was supplied, change to device view as start
        self.app.switch_screen("device")

    @on(DirectoryTree.FileSelected, "#directory_tree")
    def _file_selected(self, event: DirectoryTree.FileSelected) -> None:
        if event.path.name.endswith(".dmap"):
            self.query_one("#field_map_file", Input).value = event.path.as_posix()

    @on(Button.Pressed, "#Btn_refresh_dir")
    def _pressed_refresh_dir(self) -> None:
        root_dir = self.query_one("#field_root_dir", Input).value
        if os.path.isdir(root_dir):
            self.query_one("#directory_tree", DirectoryTree).path = root_dir
            self.query_one("#directory_tree", DirectoryTree).refresh()
        else:
            self.notify(f'Error: Directory "{root_dir}" does not exist!',
                        title="Directory not found",
                        severity="warning",
                        )


class DeviceView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

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
            id="devices",
            classes="main_col")

    def on_mount(self) -> None:

        def change_is_open(open: bool) -> None:
            self.query_one("#label_device_status", Label).update("Device is "+("open" if open else "closed"))
            self.query_one("#btn_open_close_device", Button).label = "Close" if open else "Open"
            self.query_one("#btn_open_close_device", Button).disabled = self.app.deviceAlias is None

        self.watch(self.app, "isOpen", change_is_open)

    @on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        self.app.dmapFilePath = self.query_one("#field_map_file", Input).value

    @on(Button.Pressed, "#btn_open_close_device")
    def _pressed_open_close_device(self) -> None:
        self.app.isOpen = not self.app.isOpen
