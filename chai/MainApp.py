from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual import log
from textual.widgets import Static
from textual.reactive import Reactive

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


class DmapScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DeviceView()
        yield Footer()


class DeviceScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Static("This is the Device screen")
        yield Footer()


class PropertiesScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Static("This is the Properties screen")
        yield Footer()


class RegisterScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield RegisterView()
        yield Footer()


class MetaDataScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Static("This is the MetaData screen")
        yield Footer()


class ContentScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataView()
        yield Footer()


class OptionsScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield ActionsView()
        yield Footer()


class MainScreen(Screen):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConsoleHardwareInterface()
        yield Footer()


class LayoutApp(App):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"
    SCREENS = {"dmap": DmapScreen, "device": DeviceScreen, "properties": PropertiesScreen,
               "register": RegisterScreen, "metadata": MetaDataScreen, "content": ContentScreen, "options": OptionsScreen}
    BINDINGS = [
        # TODO: seperate bindings from displayed text, so that it is not removed when key is bind by another action in some field. Or give priority to the main screen bindings
        Binding(key="ctrl+m", key_display="^m", tooltip="Load dmap file", action="switch_screen('dmap')", description="dmap"), Binding(
            key="ctrl+d", key_display="^d", tooltip="Select Device", action="switch_screen('device')", description="dev"),
        Binding(
            key="ctrl+i", key_display="^i", tooltip="Show Device Properties", action="switch_screen('properties')", description="devInfo"),
        Binding(
            key="ctrl+r", key_display="^r", tooltip="Show Register Tree", action="switch_screen('register')", description="reg"),
        Binding(
            key="ctrl+e", key_display="^e", tooltip="Show Register Meta Data", action="switch_screen('metadata')", description="meta"),
        Binding(
            key="ctrl+a", key_display="^a", tooltip="Show Register Content", action="switch_screen('content')", description="content"),
        Binding(
            key="ctrl+o", key_display="^o", tooltip="Show Options", action="switch_screen('options')", description="opts"),
    ]

    dmap_file_path: Reactive[str | None] = Reactive(None)

    device_alias: Reactive[str | None] = Reactive(None)
    device_cdd: Reactive[str | None] = Reactive(None)
    currentDevice: da.Device | None = None

    is_open: Reactive[bool] = Reactive(False)

    currentRegister: Reactive[da.GeneralRegisterAccessor | None] = Reactive(None)

    def on_mount(self) -> None:
        self.push_screen("dmap")
        self.push_screen("device")
        self.push_screen("properties")
        self.push_screen("register")
        self.push_screen("metadata")
        self.push_screen("content")
        self.push_screen("options")
        self.switch_screen("dmap")
        # self.push_screen(MainScreen()) # uncomment to see the original layout with all views visible

    def exit(self) -> None:
        if self.currentDevice:
            self.currentDevice.close()
        super().exit()

    def watch_device_alias(self, new_alias: str) -> None:
        self.currentDevice = da.Device(new_alias)
