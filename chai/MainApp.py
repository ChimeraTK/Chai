from collections import defaultdict
from itertools import groupby
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual import log
from textual.widgets import Static, Button
from textual.widgets._footer import FooterKey, FooterLabel
from textual.reactive import Reactive

from textual.css import query
from textual.widget import Widget

import socket

import deviceaccess as da

from chai.DeviceView import DeviceView, DeviceProperties, DmapView
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


class NaviFooter(Footer):

    def compose(self):
        if not self._bindings_ready:
            return
        active_bindings = self.screen.active_bindings
        bindings = [
            (binding, enabled, tooltip)
            for (_, binding, enabled, tooltip) in active_bindings.values()
            if binding.show
        ]
        action_to_bindings: defaultdict[str, list[tuple[Binding, bool, str]]]
        action_to_bindings = defaultdict(list)
        for binding, enabled, tooltip in bindings:
            action_to_bindings[binding.action].append((binding, enabled, tooltip))

        self.styles.grid_size_columns = len(action_to_bindings)

        groups = []
        keys = []
        firstGroup = True
        for group, multi_bindings_iterable in groupby(
            action_to_bindings.values(),
            lambda multi_bindings: multi_bindings[0][0].group,
        ):
            groups.append(group)
            keys.append(list(multi_bindings_iterable))

        zipped = zip(groups, keys)
        # sorted by group description, None groups last
        sorted_zipped = sorted(
            zipped, key=lambda pair: (pair[0] is None, pair[0].order if pair[0] else "")
        )
        groups, keys = zip(*sorted_zipped) if sorted_zipped else ([], [])
        for group, multi_bindings_iterable in zip(groups, keys):
            if group is not None:
                for multi_bindings in multi_bindings_iterable:
                    if not firstGroup:
                        yield FooterLabel("|")
                    firstGroup = False
                    binding, enabled, tooltip = multi_bindings[0]
                    yield FooterKey(
                        key=binding.key,
                        key_display=group.description,
                        description="",
                        action=binding.action,
                        disabled=not enabled,
                        tooltip=tooltip or binding.description,
                        classes="-grouped",
                    ).data_bind(Footer.compact)

            else:
                for multi_bindings in multi_bindings_iterable:
                    binding, enabled, tooltip = multi_bindings[0]
                    yield FooterKey(
                        binding.key,
                        self.app.get_key_display(binding),
                        binding.description,
                        binding.action,
                        disabled=not enabled,
                        tooltip=tooltip,
                    ).data_bind(Footer.compact)


class DmapScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DmapView()
        yield NaviFooter()


class DeviceScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DeviceView()
        yield NaviFooter()


class PropertiesScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DeviceProperties()
        yield NaviFooter()


class RegisterScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield RegisterView()
        yield NaviFooter()


class MetaDataScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Static("This is the MetaData screen")
        yield NaviFooter()


class ContentScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataView()
        yield NaviFooter()


class OptionsScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield ActionsView()
        yield NaviFooter()


class MainScreen(Screen):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield ConsoleHardwareInterface()
        yield Footer()


class SortedGroup(Binding.Group):
    order: int = 0

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop("order", 0)
        super().__init__(*args, **kwargs)


class LayoutApp(App):
    CSS_PATH = "Chai.tcss"
    TITLE = "Console Hardware Interface"
    SUB_TITLE = f"@ {socket.gethostname()}"
    SCREENS = {"dmap": DmapScreen, "device": DeviceScreen, "properties": PropertiesScreen,
               "register": RegisterScreen, "metadata": MetaDataScreen, "content": ContentScreen, "options": OptionsScreen}
    BINDINGS = [
        # TODO: seperate bindings from displayed text, so that it is not removed when key is bind by another action in some field. Or give priority to the main screen bindings
        Binding(key="ctrl+m", priority=True, tooltip="Load dmap file",
                action="switch_screen('dmap')", description="dmap Screen", group=SortedGroup("dmap", order=0)),
        Binding(
            key="ctrl+d", priority=True, tooltip="Select Device", action="switch_screen('device')", description="Device Screen", group=SortedGroup("devices", order=1)),
        Binding(
            key="ctrl+i", priority=True, tooltip="Show Device Properties", action="switch_screen('properties')", description="Device Property Screen", group=SortedGroup("properties", order=2)),
        Binding(
            key="ctrl+r", priority=True, tooltip="Show Register Tree", action="switch_screen('register')", description="Device Register Screen", group=SortedGroup("registers", order=3)),
        Binding(
            key="ctrl+e", priority=True, tooltip="Show Register Meta Data", action="switch_screen('metadata')", description="Register Metadata Screen", group=SortedGroup("meta", order=4)),
        Binding(
            key="ctrl+a", priority=True, tooltip="Show Register Content", action="switch_screen('content')", description="Register Content Screen", group=SortedGroup("content", order=5)),
        Binding(
            key="ctrl+o", priority=True, tooltip="Show Options", action="switch_screen('options')", description="Options Screen", group=SortedGroup("options", order=6)),
    ]

    dmapFilePath: Reactive[str | None] = Reactive(None)

    deviceAlias: Reactive[str | None] = Reactive(None)
    deviceCdd: Reactive[str | None] = Reactive(None)
    currentDevice: Reactive[da.Device | None] = Reactive(None)

    isOpen: Reactive[bool] = Reactive(False)

    currentRegister: Reactive[da.GeneralRegisterAccessor | None] = Reactive(None)
    registerInfo: Reactive[da.pb.RegisterInfo | None] = Reactive(None)
    registerValueChanged: Reactive[int] = Reactive(int)  # value does not matter, change informs about read operation

    def on_mount(self) -> None:
        self.push_screen("device")
        self.push_screen("properties")
        self.push_screen("register")
        self.push_screen("metadata")
        self.push_screen("content")
        self.push_screen("options")
        self.push_screen("dmap")
        # self.push_screen(MainScreen()) # uncomment to see the original layout with all views visible

    def watch_deviceAlias(self, new_alias: str) -> None:
        self.currentDevice = da.Device(new_alias)

    def watch_isOpen(self, open: bool) -> None:
        if self.currentDevice is None:
            return
        if open:
            self.currentDevice.open()
        else:
            self.currentDevice.close()
