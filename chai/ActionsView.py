from __future__ import annotations
from typing import TYPE_CHECKING
from textual.widgets._radio_button import RadioButton
if TYPE_CHECKING:
    from MainApp import LayoutApp
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Checkbox, RadioSet, RadioButton

from textual import on

import deviceaccess as da
from datetime import datetime

from collections import deque


class ActionsView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    def compose(self) -> ComposeResult:
        self.add_class("main_col")

        yield Label("Options")
        yield Vertical(
            Checkbox("Read after write",  compact=True, id="checkbox_read_after_write"),
            Checkbox("Autoselect previous register", compact=True, id="checkbox_autoselect"),
            Checkbox("Sort registers", compact=True, id="checkbox_sort_registers"),

            Label("Poll frequency", id="label_poll_update_frq"),
            RadioSet(
                RadioButton("1 Hz", value=False, id="radio_hz_1"),
                RadioButton("30 Hz", value=True, id="radio_hz_30"),
                RadioButton("100 Hz", value=False, id="radio_hz_100"),
                disabled=True,
                compact=True,
                id="radio_set_freq"
            ),

        )

    def update(self) -> None:
        self.app.pushMode = self.app.register is not None and    \
            da.AccessMode.wait_for_new_data in self.app.register.accessor.getAccessModeFlags()

        self.query_one("#label_poll_update_frq", Label).visible = not self.app.pushMode
        self.query_one("#radio_set_freq", RadioSet).visible = not self.app.pushMode
        self.query_one("#radio_set_freq", RadioSet).disabled = True

    def on_mount(self) -> None:
        self.watch(self.app, "register", lambda register: self.update())
        self.watch(self.app, "isOpen", lambda open: self.update())

        self.watch(self.app, "continuousRead", self.updateRadioSetFrqButtons)
        self.query_one("#checkbox_sort_registers", Checkbox).value = self.app.sortedRegisters
        self.query_one("#checkbox_autoselect", Checkbox).value = self.app.autoSelectPreviousRegister
        self.update()

    def updateRadioSetFrqButtons(self) -> None:
        if not self.app.pushMode:
            self.query_one("#radio_set_freq").disabled = not self.app.continuousRead

    def on_unmount(self):
        if self.app.pushMode and self.app.register is not None:
            self.app.register.accessor.interrupt()

    @on(Checkbox.Changed, "#checkbox_read_after_write")
    def on_read_after_write_changed(self, changed: Checkbox.Changed):
        self.app.readAfterWrite = changed.control.value

    def on_radio_set_changed(self, changed: RadioSet.Changed) -> None:
        set = self.query_one("#radio_set_freq", RadioSet)
        assert set.pressed_button is not None
        assert set.pressed_button.id is not None
        assert set.pressed_button.id.startswith("radio_hz_")
        hz = int(set.pressed_button.id[9:])
        self.app.continuousPollHz = hz

    @on(Checkbox.Changed, "#checkbox_sort_registers")
    def _checkbox_sort_changed(self, changed: Checkbox.Changed) -> None:
        self.app.sortedRegisters = changed.control.value

    @on(Checkbox.Changed, "#checkbox_autoselect")
    def _checkbox_autoselect_changed(self, changed: Checkbox.Changed) -> None:
        self.app.autoSelectPreviousRegister = changed.control.value
