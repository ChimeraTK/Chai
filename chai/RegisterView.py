from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

from textual.events import Mount
if TYPE_CHECKING:
    from MainApp import LayoutApp
    from textual.widgets.tree import TreeNode

from chai.Utils import InputWithEnterAction
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Button, Label, Tree, Input, Checkbox, Button, Input, Sparkline
from textual import log, on
from textual.reactive import Reactive
from textual.validation import Validator, ValidationResult
from textual.events import Click
from textual.screen import ModalScreen

from chai.DataView import RegisterInfo, RegisterValueField
from chai.ActionsView import ActionsView

from chai import Utils

import deviceaccess as da
import re

from chai.Utils import AccessorHolder


class RegisterTree(Tree):

    _tree: Tree[dict] = Tree("Registers")
    _register_names = []
    regExPattern: Reactive[str] = Reactive("")
    if TYPE_CHECKING:
        app: LayoutApp

    def on_mount(self) -> None:
        self.watch(self.app, "currentDevice", lambda device: self.on_device_changed(device))

    def on_device_changed(self, device: da.Device) -> None:
        self._tree.clear()
        if device is None:
            return

        register_names = []
        cat = device.getRegisterCatalogue()
        for reg in cat:
            register_names.append(str(reg.getRegisterName()))
        for reg in cat.hiddenRegisters():
            name: str = reg.getRegisterName()
            log(f"Hidden register: {name}")
            if name.startswith("/DUMMY_INTERRUPT_"):
                register_names.append(str(name))
        self._register_names = register_names
        self.updateTree()

    def updateTree(self) -> None:
        self._tree.clear()
        if self.app.currentDevice is None:
            return

        if self.app.sortedRegisters:
            self._register_names.sort()

        for reg_name in self._register_names:
            match = re.search(self.regExPattern, reg_name, flags=re.IGNORECASE)
            if len(self.regExPattern) > 0 and not match:
                continue
            split_name = reg_name.split('/')[1:]
            current_level = self._tree.root
            while len(split_name) > 1:
                node_added = False
                for child in current_level.children:
                    if str(child.label) == split_name[0]:
                        current_level = child
                        node_added = True
                        break
                if not node_added:
                    current_level = current_level.add(split_name[0])
                split_name = split_name[1:]

            current_level.add_leaf(split_name[0])

    def compose(self) -> ComposeResult:
        self._tree.root.expand()
        self._tree.show_root = False
        yield self._tree

    def on_tree_node_selected(self, selected):
        if selected.node.is_root:
            return

        currentRegisterPath = f"/{selected.node.label}"
        parent = selected.node.parent
        while not parent.is_root:
            currentRegisterPath = f"/{parent.label}{currentRegisterPath}"
            parent = parent.parent

        if currentRegisterPath not in self._register_names:
            return

        if self.app.currentDevice is None:
            return

        self.app.registerPath = currentRegisterPath

    def checkAutoSelectPreviousRegister(self) -> None:
        return
        # TODO: re-enable auto-select previous register
        if not self.app.autoSelectPreviousRegister:
            return
        if self.app.currentDevice is None:
            return
        if self.app.previouslySelectedRegister is None:
            return
        for node in self.walk(self._tree.root):
            if node.label == self.app.previouslySelectedRegister:
                node.select()
                break

    def walk(self, node):
        yield node
        for child in node.children:
            yield from self.walk(child)

    def watch_regExPattern(self, value: str) -> None:
        if self.app.currentDevice is None:
            return
        self.on_device_changed(self.app.currentDevice)


class MetaPopUpScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Vertical(
            RegisterInfo(id="register_info"),
            Button("Close", id="metadata_dialog_close"),
            id="metadata_dialog",
        )

    @on(Button.Pressed, "#metadata_dialog_close")
    def pressed_close(self) -> None:
        self.app.pop_screen()


class RegisterView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    _avg_update_interval_list: deque = deque(maxlen=10)
    _registerValueQueue: deque = deque(maxlen=80)

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Container(
                RegisterTree("Registers"),
                Container(
                    InputWithEnterAction(id="regex_input", placeholder="Regex to filter registers",
                                         action=self.RefreshTree, validators=[RegExValidator()], compact=False),
                    Container(
                        Button("Collapse all", id="btn_collapse"),
                        Button("Expand all", id="btn_expand"),
                        id="registerTreeNodeControls"),

                    classes="RegisterViewControls"
                ),
                id="registers",
                classes="left_pane"),
            Container(
                RegisterValueField(id="register_value_field"),
                Container(
                    Container(
                        Label("Channel:", id="channelNumberLabel"),
                        Input(value="0", placeholder="0", id="channel_input", type="integer", compact=True),
                        id="channel_input_container"
                    ),
                    Button("Read", disabled=True, id="btn_read"),
                    Button("Write", disabled=True, id="btn_write"),
                    id="content_action_buttons"
                ),
                Container(
                    Label("(placeholder)", id="label_ctn_pollread"),
                    Checkbox("",  compact=True, id="checkbox_cont_pollread", value=False, disabled=True),
                    classes="small_row",
                ),
                id="register_content",
                classes="right_pane"),
        )
        yield Sparkline(id="register_value_sparkline",
                        data=self._registerValueQueue,
                        summary_function=max)
        yield Container(
            Label("(placeholder)", id="label_last_poll_update"),

            Label("(never)", id="last_update_time"),
            Label("Avg. update Δ", id="label_avg_update_interval"),
            Label("(n/a)", id="update_interval"),
            classes="poll_status_bar"
        )

    def on_mount(self, event: Mount) -> None:
        self.query_one("#btn_read", Button).disabled = not self.app.enableReadButton
        self.query_one("#btn_write", Button).disabled = not self.app.enableWriteButton
        self.query_one("#btn_write", Button).label = "Write" if not self.app.dummyWrite else "Write (dummy)"
        self.query_one("#channel_input_container").display = False
        self.watch(self.app, "continuousRead", lambda cr: self._update_read_write_btn_status())
        self.watch(self.app, "isOpen", lambda cr: self._update_read_write_btn_status())
        self.watch(self.app, "register", lambda cr: self._update_read_write_btn_status())
        self.watch(self.app, "sortedRegisters", lambda cr: self.RefreshTree())
        self.watch(self.app, "channel", lambda channel: self.on_channel_changed(channel))
        self.watch(self.app, "registerValueChanged", lambda old, new: self.on_registerValueChanged(old, new))
        self.watch(self.app, "register", lambda register: self.update())
        self.watch(self.app, "isOpen", lambda open: self.update())
        self.update()

    def update(self) -> None:
        self.query_one("#label_ctn_pollread", Label).update(
            "Continuous Read" if self.app.pushMode else "Continuous Poll")
        self.query_one("#label_last_poll_update", Label).update(
            "Last update:" if self.app.pushMode else "Last poll:")
        self.query_one("#checkbox_cont_pollread", Checkbox).disabled = not self.app.enableReadButton
        self.query_one("#checkbox_cont_pollread", Checkbox).value = False
        self.app.continuousRead = False
        self._registerValueQueue.clear()

    def on_registerValueChanged(self, old_time: datetime, new_time: datetime) -> None:
        self.query_one("#last_update_time", Label).update(str(new_time))
        if not self.app.continuousRead:
            self.query_one("#update_interval", Label).display = False
            self.query_one("#label_avg_update_interval", Label).display = False
            return
        else:
            self.query_one("#update_interval", Label).display = True
            self.query_one("#label_avg_update_interval", Label).display = True
        if old_time is not None:
            self._avg_update_interval_list.append((new_time - old_time).total_seconds())
            avg = sum(self._avg_update_interval_list) / len(self._avg_update_interval_list)
            self.query_one("#update_interval", Label).update(f"{round(avg * 1000)} ms")
            sparkline = self.query_one("#register_value_sparkline", Sparkline)
            table = self.query_one("#register_value_field", RegisterValueField)
            if (len(self._registerValueQueue) == self._registerValueQueue.maxlen):
                self._registerValueQueue.popleft()
                # don't add duplicate values
                return
            self._registerValueQueue.append(table.currentlySelectedValue())

            sparkline.refresh()

    def RefreshTree(self) -> None:
        rt = self.query_one(RegisterTree)
        rt.refresh()

    def on_channel_changed(self, channel: int) -> None:
        self.query_one("#channel_input", Input).value = str(channel)

    def on_input_submitted(self, change: Input.Submitted) -> None:
        if self.app.register is None:
            change.input.value = str(self.app.channel)
            return
        _nChannels = self.app.register.info.getNumberOfChannels()
        if change.value.isdigit():
            value = int(change.value)
        else:
            # might be empty...
            value = 0
        if value >= _nChannels:
            value = _nChannels - 1
            change.input.value = str(value)
            self.notify("Channel out of range.", severity="warning")
        self.app.channel = value

    def _update_read_write_btn_status(self):
        if self.app.register is not None:
            self.query_one("#btn_read").disabled = (
                self.app.continuousRead or
                not self.app.register.accessor.isReadable())
            self.query_one("#btn_write").disabled = (
                self.app.continuousRead or
                not self.app.register.accessor.isWriteable())
            if self.app.register.info.getNumberOfChannels() < 2:
                self.query_one("#channel_input_container").display = False
            else:
                self.query_one("#channel_input_container").display = True
                self.query_one("#channelNumberLabel", Label).update(
                    f"Ch. (0-{self.app.register.info.getNumberOfChannels()-1}):")

    @on(Button.Pressed, "#btn_collapse")
    def _pressed_collapse(self) -> None:
        rt = self.query_one(RegisterTree)
        rt._tree.root.collapse_all()

    @on(Button.Pressed, "#btn_expand")
    def _pressed_expand(self) -> None:
        rt = self.query_one(RegisterTree)
        rt._tree.root.expand_all()

    @on(Input.Changed, "#regex_input")
    def _regex_changed(self, event: Input.Changed) -> None:
        if not event.validation_result:
            return
        if not event.validation_result.is_valid:
            self.notify("Invalid regex pattern.", severity="error")
            return
        rt = self.query_one(RegisterTree)
        inp = self.query_one("#regex_input", InputWithEnterAction)
        rt.regExPattern = inp.value
        self._pressed_expand()

    @on(Click)
    def _on_right_click(self, event: Click) -> None:
        if event.button == 3 and isinstance(event.widget, Tree) and "node" in event.style.meta:
            tree = self.query_one(RegisterTree)
            for node in tree.walk(tree._tree.root):
                n: TreeNode = node

                if n._id == event.style.meta["node"]:
                    if self.app.registerPath is None:
                        return
                    if n.label is None:
                        return
                    if self.app.registerPath.endswith(n.label.plain):
                        # self.app.switch_screen("metadata")
                        self.app.push_screen(MetaPopUpScreen())

                    break

    @on(Checkbox.Changed, "#checkbox_cont_pollread")
    def on_checkbox_changed(self, changed: Checkbox.Changed):
        self.app.continuousRead = changed.control.value

    def updateSparkline(self) -> None:
        if self.app.register is None:
            return
        if self.app.registerValue is None:
            return
        if not self.app.continuousRead:
            return
        self._registerValueQueue.append(self.app.registerValue)
        sparkline = self.query_one("#register_value_sparkline", Sparkline)
        sparkline.refresh()
        sparkline.data = list(self._registerValueQueue)


class RegExValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        try:
            re.compile(value, flags=re.IGNORECASE)
            return self.success()
        except re.error:
            return self.failure("Invalid regex pattern.")
