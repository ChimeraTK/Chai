from pathlib import Path
from typing import TYPE_CHECKING, Iterable
if TYPE_CHECKING:
    from MainApp import LayoutApp
from textual.worker import Worker
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Button, Label, Static, Input, Button, ListView, ListItem, Input, DirectoryTree, Checkbox
from textual.events import Click, MouseEvent
from textual import on, log

import deviceaccess as da

from chai.RegisterView import RegisterTree
from chai.Utils import InputWithEnterAction

import os
import sys
from collections.abc import Iterator


class DeviceList(ListView):

    _devices: dict[str, str] = {}
    if TYPE_CHECKING:
        app: LayoutApp

    def updateDmapFile(self, filename: str):
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
                                title="Parsing error", severity="warning")
                    return {}

                alias_name, cdd = splitline
                devices[alias_name.strip()] = cdd.strip()
        except FileNotFoundError:
            self.notify(f"Could not open file: {dmapPath}", title="File not found", severity="warning")
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


class DmapTree(DirectoryTree):

    onlyDmap: bool = True
    showHidden: bool = False

    def __init__(self, *args, **kwargs):
        self.onlyDmap = kwargs.pop("onlyDmap", True)
        self.showHidden = kwargs.pop("showHidden", False)
        super().__init__(*args, **kwargs)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        if self.showHidden:
            return paths
        else:
            return (p for p in paths if p.is_dir and not p.name.startswith("."))

    def _directory_content(self, location: Path, worker: Worker) -> Iterator[Path]:
        try:
            for entry in location.iterdir():
                if worker.is_cancelled:
                    break
                if (entry.is_file() and self.onlyDmap and not entry.name.endswith(".dmap")):
                    continue
                if not self.showHidden and entry.name.startswith("."):
                    continue
                yield entry
        except PermissionError:
            pass


class DmapView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Pick dmap file from tree with root (enter to refresh):"),
            InputWithEnterAction(id="field_root_dir", value=os.getcwd(),
                                 placeholder="Root directory", action=self._pressed_refresh_dir),
            DmapTree("./", onlyDmap=True, showHidden=False, id="directory_tree"),
            Container(
                Checkbox("Show hidden", id="checkbox_show_hidden", value=False, compact=True),
                Checkbox("Only show .dmap files", id="checkbox_only_dmap", value=True, compact=True), classes="small_row"),
            Label("Or enter dmap file path directly (enter to load):"),
            Container(
                InputWithEnterAction(placeholder="*.dmap", id="field_map_file", action=self._pressed_load_boards),
                Button("Load dmap file", id="Btn_load_boards"),
                classes="small_row"),
            id="devices",
            classes="main_col")

    def on_mount(self) -> None:
        self.query_one("#directory_tree", DirectoryTree).guide_depth = 2
        if len(sys.argv) > 1:
            self.query_one("#field_map_file", Input).value = sys.argv[1]
            self.query_one("#Btn_load_boards", Button).press()

    @on(Button.Pressed, "#Btn_load_boards")
    def _pressed_load_boards(self) -> None:
        mapFieldValue = self.query_one("#field_map_file", Input).value
        rootpath = self.query_one("#field_root_dir", Input).value
        self.app.dmapFilePath = os.path.join(rootpath, mapFieldValue)
        self.app.switch_screen("device")

    @on(DirectoryTree.FileSelected, "#directory_tree")
    def _file_selected(self, event: DirectoryTree.FileSelected) -> None:
        if event.path.is_file():
            self.query_one("#field_map_file", Input).value = str(
                event.path.relative_to(self.query_one("#field_root_dir", Input).value))

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

    @on(Checkbox.Changed, "#checkbox_show_hidden")
    def _checkbox_show_hidden_changed(self, event: Checkbox.Changed) -> None:
        self.query_one("#directory_tree", DmapTree).showHidden = event.value
        self.query_one("#directory_tree", DmapTree).reload()

    @on(Checkbox.Changed, "#checkbox_only_dmap")
    def _checkbox_only_dmap_changed(self, event: Checkbox.Changed) -> None:
        self.query_one("#directory_tree", DmapTree).onlyDmap = event.value
        self.query_one("#directory_tree", DmapTree).reload()

    @on(Click, "#directory_tree")
    def _on_double_click(self, event: Click) -> None:
        if event.chain >= 2:  # double click
            tree = self.query_one("#directory_tree", DmapTree)
            selectedNode = tree.cursor_node
            if selectedNode is not None:
                data = selectedNode.data
                if data is not None and data.path.is_file():
                    self.query_one("#field_map_file", Input).value = str(
                        data.path.relative_to(self.query_one("#field_root_dir", Input).value))
                    self._pressed_load_boards()


class DeviceView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                DeviceList(id="device_list"),
                Container(
                    Label("No device loaded.", id="label_device_status"),
                    Button("Open", id="btn_open_close_device", disabled=True),
                    id="device_status_container",
                ),
                id="device_list_top_container",
            ),
            Static("Opened device CDD:", id="label_device_cdd_header"),
            Label("-", id="field_device_identifier"),
            id="devices",
            classes="main_col")

    def on_mount(self) -> None:

        def change_is_open(open: bool) -> None:
            self.query_one("#label_device_status", Label).update("Device is "+("open" if open else "closed"))
            self.query_one("#btn_open_close_device", Button).label = "Close" if open else "Open"
            self.query_one("#btn_open_close_device", Button).disabled = self.app.deviceAlias is None

        self.watch(self.app, "isOpen", change_is_open)

        self.watch(self.app, "deviceCdd", lambda cdd: self.query_one(
            "#field_device_identifier", Label).update(cdd or "-"))

    @on(Button.Pressed, "#btn_open_close_device")
    def _pressed_open_close_device(self) -> None:
        self.app.isOpen = not self.app.isOpen

    @on(Click)
    def _on_double_click(self, event: Click) -> None:
        if event.chain >= 2 and isinstance(event.widget, Label) and isinstance(event.widget.parent, ListItem):
            item: ListItem | None = event.widget.parent
            list: DeviceList = self.query_one("#device_list", DeviceList)
            if list.index is None or item is None:
                return
            list.on_list_view_selected(ListView.Selected(list, item, list.index))
            # TODO: bad devices should not result in a switch to register screen
            if self.app.isOpen:
                self.app.switch_screen("register")
