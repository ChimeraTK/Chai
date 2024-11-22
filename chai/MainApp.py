from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal,  Container
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual import on

import socket

import deviceaccess as da

from chai.DeviceView import DeviceView
from chai.RegisterView import RegisterView
from chai.OptionsView import OptionsView


class ConsoleHardwareInterface(Container):

    BINDINGS = [
        ("d", "show_tab('d')", "Device view"),
        ("r", "show_tab('r')", "Register view"),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="d"):
            with TabPane("Device", id="d"):
                yield DeviceView()
            with TabPane("Registers", id="r"):
                yield RegisterView()

            # TODO: Implement the Options tab
            with TabPane("Options", id="o"):
                yield OptionsView()

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab


class MainScreen(Screen):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConsoleHardwareInterface()
        yield Footer(id="footer")


class LayoutApp(App):
    currentDevice: da.Device = None
    currentRegister: da.GeneralRegisterAccessor = None
    dmap_file_path: str = None

    def __init__(self, root_dir: str, dmap_file: str):
        self.root_dir = root_dir
        self.dmap_file_path = dmap_file
        super().__init__()

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def exit(self) -> None:
        print("closed")
        if self.currentDevice:
            self.currentDevice.close()
        super().exit()
