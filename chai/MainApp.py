from chai.DeviceView import DeviceView, DeviceProperties, DmapView
from chai.RegisterView import RegisterView
from chai.DataView import DataView, RegisterInfo
from chai.ActionsView import ActionsView
from chai.Utils import AccessorHolder
from chai import Utils
from chai.ExceptionDialog import ExceptionDialog

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual import log
from textual.widgets import Static, Button
from textual.widgets._footer import FooterKey, FooterLabel
from textual.reactive import Reactive
from textual import on, work
from textual.worker import get_current_worker
from textual.timer import Timer

from collections import defaultdict
from datetime import datetime
from itertools import groupby
import socket
import deviceaccess as da


class ConsoleHardwareInterface(Container):

    def compose(self) -> ComposeResult:
        yield Horizontal(
            DeviceView(),
            RegisterView(),
            DataView(),
            ActionsView()
        )


class NaviFooter(Footer):
    currentScreen: str

    def __init__(self, *args, **kwargs):
        self.currentScreen = kwargs.pop("currentScreen")
        super().__init__(*args, **kwargs)

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
                        classes="-grouped" + ("" if group.description != self.currentScreen else " selected"),
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
        yield NaviFooter(currentScreen="dmap")


class DeviceScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DeviceView()
        yield NaviFooter(currentScreen="devices")


class PropertiesScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DeviceProperties()
        yield NaviFooter(currentScreen="properties")


class RegisterScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield RegisterView()
        yield NaviFooter(currentScreen="registers")


class MetaDataScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield RegisterInfo(id="register_info")
        yield NaviFooter(currentScreen="meta")


class ContentScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataView()
        yield NaviFooter(currentScreen="content")


class OptionsScreen(Screen):

    def compose(self) -> ComposeResult:
        yield Header()
        yield ActionsView()
        yield NaviFooter(currentScreen="options")


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
        # Properties screen currently not very useful
        # Binding(
        #    key="ctrl+i", priority=True, tooltip="Show Device Properties", action="switch_screen('properties')", description="Device Property Screen", group=SortedGroup("properties", order=2)),
        Binding(
            key="ctrl+r", priority=True, tooltip="Show Register Tree", action="switch_screen('register')", description="Device Register Screen", group=SortedGroup("registers", order=3)),
        Binding(
            key="ctrl+e", priority=True, tooltip="Show Register Meta Data", action="switch_screen('metadata')", description="Register Metadata Screen", group=SortedGroup("meta", order=4)),
        # Binding(
        #    key="ctrl+a", priority=True, tooltip="Show Register Content", action="switch_screen('content')", description="Register Content Screen", group=SortedGroup("content", order=5)),
        Binding(
            key="ctrl+o", priority=True, tooltip="Show Options", action="switch_screen('options')", description="Options Screen", group=SortedGroup("options", order=6)),
    ]

    _update_timer: Timer | None = None

    dmapFilePath: Reactive[str | None] = Reactive(None)

    deviceAlias: Reactive[str | None] = Reactive(None)
    deviceCdd: Reactive[str | None] = Reactive(None)
    currentDevice: Reactive[da.Device | None] = Reactive(None)

    isOpen: Reactive[bool] = Reactive(False)

    registerPath: Reactive[str | None] = Reactive(None)
    register: Reactive[AccessorHolder | None] = Reactive(None)
    registerValueChanged: Reactive[datetime | None] = Reactive(None)  # value is timestamp of change

    channel: Reactive[int] = Reactive(0)
    readAfterWrite: Reactive[bool] = Reactive(False)
    continuousRead: Reactive[bool] = Reactive(False)
    sortedRegisters: Reactive[bool] = Reactive(False)
    autoSelectPreviousRegister: bool = True
    previouslySelectedRegister: str | None = None
    pushMode: bool = False
    dummyWrite: bool = False
    enableReadButton: bool = False
    enableWriteButton: bool = False
    continuousPollHz: Reactive[float] = Reactive(1.)

    def on_mount(self) -> None:
        self.push_screen("device")
        # self.push_screen("properties") # currently not useful
        self.push_screen("register")
        self.push_screen("metadata")
        # self.push_screen("content")
        self.push_screen("options")
        self.push_screen("dmap")
        # self.push_screen(MainScreen()) # uncomment to see the original layout with all views visible

    def watch_deviceAlias(self, new_alias: str) -> None:
        self.registerPath = None
        try:
            self.currentDevice = da.Device(new_alias)
        except RuntimeError as e:
            self.app.push_screen(ExceptionDialog(f"Error while creating device '{new_alias}'", e, False))

    def watch_isOpen(self, open: bool) -> None:
        if self._update_timer is not None:
            self._update_timer.stop()
            self._update_timer = None

        if self.pushMode and self.register is not None:
            self.register.accessor.interrupt()

        if self.currentDevice is None:
            return

        if open:
            try:
                self.currentDevice.open()
                self.watch_registerPath(self.registerPath)
            except RuntimeError as e:
                self.app.push_screen(ExceptionDialog(f"Error while opening device '{self.deviceAlias}'", e, False))
        else:
            self.currentDevice.close()
            self.enableReadButton = False
            self.enableWriteButton = False

        if open and self.register is not None and self.register.accessor.isReadable():
            try:
                self.register.accessor.readLatest()
                self.registerValueChanged = datetime.now()
            except RuntimeError as e:
                self.app.push_screen(ExceptionDialog("Error while reading from device", e, False))

    def watch_registerPath(self, path: str | None) -> None:
        if path is None or self.currentDevice is None:
            self.register = None
            return

        rc = self.currentDevice.getRegisterCatalogue()
        info = rc.getRegister(path)

        dd = info.getDataDescriptor()
        if da.AccessMode.raw in info.getSupportedAccessModes():
            # raw transfers are supported
            np_type = Utils.get_raw_numpy_type(dd.rawDataType())
            flags = [da.AccessMode.raw]
        else:
            # no raw transfer supported
            np_type = Utils.get_raw_numpy_type(dd.minimumDataType())
            flags = []

        dummyWriteFlags = flags

        if da.AccessMode.wait_for_new_data in info.getSupportedAccessModes():
            # we cannot use raw and wait_for_new_data at the same time
            self.currentDevice.activateAsyncRead()
            flags = [da.AccessMode.wait_for_new_data]

        dummyWritePath = path+".DUMMY_WRITEABLE"
        self.dummyWrite = not info.isWriteable() and rc.hasRegister(dummyWritePath)

        if self.isOpen:
            self.enableReadButton = info.isReadable()
            self.enableWriteButton = info.isWriteable() or self.dummyWrite

        dummyWriteAccessor = None
        if info.getDataDescriptor().fundamentalType() != da.FundamentalType.nodata:
            accessor = self.currentDevice.getTwoDRegisterAccessor(np_type, path, accessModeFlags=flags)
            if self.dummyWrite:
                dummyWriteAccessor = self.currentDevice.getTwoDRegisterAccessor(
                    np_type, dummyWritePath, accessModeFlags=dummyWriteFlags)
        else:
            accessor = self.currentDevice.getVoidRegisterAccessor(path, accessModeFlags=flags)
            if self.dummyWrite:
                dummyWriteAccessor = self.currentDevice.getVoidRegisterAccessor(
                    dummyWritePath, accessModeFlags=dummyWriteFlags)

        self.register = AccessorHolder(accessor, info, dummyWriteAccessor)

    @on(Button.Pressed, "#btn_read")
    def _pressed_read(self) -> None:
        if self.register is None or not self.isOpen:
            return
        try:
            self.register.accessor.readLatest()
            self.registerValueChanged = datetime.now()
        except RuntimeError as e:
            self.push_screen(ExceptionDialog("Error reading from device", e, True))

    @on(Button.Pressed, "#btn_write")
    def _pressed_write(self) -> None:
        if self.register is None or not self.isOpen:
            return
        try:
            if self.register.dummyWriteAccessor is None:
                self.register.accessor.write()
            else:
                self.register.dummyWriteAccessor.write()
        except RuntimeError as e:
            self.push_screen(ExceptionDialog("Error while writing to device", e, True))
        if self.readAfterWrite and self.register.accessor.isReadable():
            self._pressed_read()

    def watch_continuousRead(self, continuousRead) -> None:
        if not self.pushMode:
            self.watch_continuousPollHz(self.continuousPollHz)
            assert self._update_timer is not None
            if continuousRead:
                self._update_timer.resume()
            else:
                self._update_timer.pause()
        else:
            if continuousRead:
                self._update_push_loop()
            else:
                if self.register is not None:
                    self.register.accessor.interrupt()

    def watch_continuousPollHz(self, hz) -> None:
        if self._update_timer is not None:
            self._update_timer.stop()
        self._update_timer = self.set_interval(1 / hz, self._pressed_read)

    def watch_register(self,  old_register: AccessorHolder, new_register: AccessorHolder) -> None:
        if self._update_timer is not None:
            self._update_timer.stop()
            self._update_timer = None

        if self.pushMode:
            old_register.accessor.interrupt()

        self.channel = 0
        if new_register is not None:
            self._isRaw = da.AccessMode.raw in new_register.accessor.getAccessModeFlags()
            if self.isOpen and new_register.accessor.isReadable():
                try:
                    new_register.accessor.readLatest()
                    self.registerValueChanged = datetime.now()
                except RuntimeError as e:
                    self.app.push_screen(ExceptionDialog("Error reading from device", e, True))

    @work(exclusive=True, thread=True)
    def _update_push_loop(self) -> None:
        worker = get_current_worker()
        register = self.register
        while not worker.is_cancelled and register is not None:
            try:
                register.accessor.read()
            except RuntimeError as e:
                self.app.call_from_thread(self._update_push_single, e)
            except da.ThreadInterrupted:
                return
            self.app.call_from_thread(self._update_push_single)

    def _update_push_single(self, exception: RuntimeError | None = None) -> None:
        if exception is not None:
            self.app.push_screen(ExceptionDialog("Error while reading from device", exception, True))
            return

        now = datetime.now()
        self.registerValueChanged = now
