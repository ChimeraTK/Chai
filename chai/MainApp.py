from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Header, Footer

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

    def exit(self) -> None:
        print("closed")
        if self.currentDevice:
            self.currentDevice.close()
        super().exit()
