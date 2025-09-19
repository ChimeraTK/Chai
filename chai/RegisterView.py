from typing import TYPE_CHECKING

from textual.events import Mount
if TYPE_CHECKING:
    from MainApp import LayoutApp
from chai.Utils import InputWithEnterAction
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Button, Label, Tree, Input, Checkbox, Button, Input
from textual import log, on
from textual.reactive import Reactive
from textual.validation import Validator, ValidationResult

from chai.DataView import RegisterValueField
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
        for reg in device.getRegisterCatalogue():
            register_names.append(reg.getRegisterName())
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

        currentRegisterPath = selected.node.label
        parent = selected.node.parent
        while not parent.is_root:
            currentRegisterPath = f"/{parent.label}/{currentRegisterPath}"
            parent = parent.parent

        if currentRegisterPath not in self._register_names:
            return

        if self.app.currentDevice is None:
            return

        self.app.registerPath = currentRegisterPath

    def watch_regExPattern(self, value: str) -> None:
        if self.app.currentDevice is None:
            return
        self.on_device_changed(self.app.currentDevice)


class RegisterView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Container(
                RegisterTree("Registers"),
                Container(
                    InputWithEnterAction(id="regex_input", placeholder="Regex to filter registers",
                                         action=self.checkRegexAndrefreshTree, validators=[RegExValidator()], compact=False),
                    Checkbox("Autoselect previous register", compact=True),
                    Checkbox("Sort registers", compact=True, id="checkbox_sort_registers"),
                    Button("Collapse all", id="btn_collapse"),
                    Button("Expand all", id="btn_expand"),

                    classes="RegisterViewControls"
                ),
                id="registers",
                classes="left_pane"),
            Container(
                RegisterValueField(id="register_value_field"),
                Vertical(
                    Button("Read", disabled=True, id="btn_read"),
                    Button("Write", disabled=True, id="btn_write"),
                ),
                id="register_content",
                classes="right_pane"),
        )

    def on_mount(self, event: Mount) -> None:
        self.query_one("#btn_read", Button).disabled = not self.app.enableReadButton
        self.query_one("#btn_write", Button).disabled = not self.app.enableWriteButton
        self.query_one("#btn_write", Button).label = "Write" if not self.app.dummyWrite else "Write (dummy)"
        self.query_one("#checkbox_sort_registers", Checkbox).value = self.app.sortedRegisters
        self.watch(self.app, "continuousRead", lambda cr: self._update_read_write_btn_status())
        self.watch(self.app, "isOpen", lambda cr: self._update_read_write_btn_status())
        self.watch(self.app, "register", lambda cr: self._update_read_write_btn_status())

    def checkRegexAndrefreshTree(self) -> None:
        rt = self.query_one(RegisterTree)
        rt.refresh()

    def _update_read_write_btn_status(self):
        if self.app.register is not None:
            self.query_one("#btn_read").disabled = (
                self.app.continuousRead or
                not self.app.register.accessor.isReadable())
            self.query_one("#btn_write").disabled = (
                self.app.continuousRead or
                not self.app.register.accessor.isWriteable())

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

    @on(Checkbox.Changed, "#checkbox_sort_registers")
    def _checkbox_sort_changed(self, changed: Checkbox.Changed) -> None:
        self.app.sortedRegisters = changed.control.value
        rt = self.query_one(RegisterTree)
        rt.updateTree()


class RegExValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        try:
            re.compile(value, flags=re.IGNORECASE)
            return self.success()
        except re.error:
            return self.failure("Invalid regex pattern.")
