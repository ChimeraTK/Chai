from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual import log

from textual.css import query
from textual.widget import Widget

import socket

import deviceaccess as da

from chai.DeviceView import DeviceView
from chai.RegisterView import RegisterView
from chai.DataView import DataView
from chai.ActionsView import ActionsView


class ConsoleHardwareInterface(Container):

    def compose(self) -> ComposeResult:
        yield Horizontal(
            DeviceView(),
            RegisterView(),
            DataView(),
            ActionsView()
        )


class MainScreen(Screen):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"
    BINDINGS = [
        # TODO: seperate bindings from displayed text, so that it is not removed when key is bind by another action in some field. Or give priority to the main screen bindings
        Binding(key="ctrl+m", key_display="^m", tooltip="Load dmap file", action="showDmapScreen", description="dmap"), Binding(
            key="ctrl+d", key_display="^d", tooltip="Select Device", action="showDeviceScreen", description="dev"),
        Binding(
            key="ctrl+i", key_display="^i", tooltip="Show Device Properties", action="showPropertiesScreen", description="devInfo"),
        Binding(
            key="ctrl+r", key_display="^r", tooltip="Show Register Tree", action="showRegisterScreen", description="reg"),
        Binding(
            key="ctrl+e", key_display="^e", tooltip="Show Register Meta Data", action="showMetaDataScreen", description="meta"),
        Binding(
            key="ctrl+a", key_display="^a", tooltip="Show Register Content", action="showContentScreen", description="content"),
        Binding(
            key="ctrl+o", key_display="^o", tooltip="Show Options", action="showOptionsScreen", description="opts"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConsoleHardwareInterface()
        yield Footer()

    def _action_showDmapScreen(self) -> None:
        log("dmap load")

    def _action_showDeviceScreen(self) -> None:
        log("device screen")

    def _action_showPropertiesScreen(self) -> None:
        log("properties screen")

    def _action_showRegisterScreen(self) -> None:
        log("register screen")

    def _action_showMetaDataScreen(self) -> None:
        log("metadata screen")

    def _action_showContentScreen(self) -> None:
        log("content screen")

    def _action_showOptionsScreen(self) -> None:
        log("options screen")


class LayoutApp(App):
    currentDevice: da.Device | None = None
    currentRegister: da.GeneralRegisterAccessor | None = None
    dmap_file_path: str | None = None

    def query_one(self, selector: str | type[query.QueryType], expect_type: type[query.QueryType] | None = None) -> query.QueryType | Widget:
        return self.children[0].query_one(selector, expect_type=expect_type)

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def exit(self) -> None:
        if self.currentDevice:
            self.currentDevice.close()
        super().exit()
