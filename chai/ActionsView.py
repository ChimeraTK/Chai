from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MainApp import LayoutApp
from chai.ExceptionDialog import ExceptionDialog
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label, Static, Checkbox, Button, RadioSet, RadioButton

from textual import on

import deviceaccess as da
from datetime import datetime

from chai.DataView import RegisterValueField

from collections import deque
from chai.Utils import AccessorHolder


class ActionsView(Vertical):
    if TYPE_CHECKING:
        app: LayoutApp

    _avg_update_interval_list: deque = deque(maxlen=10)

    def compose(self) -> ComposeResult:
        self.add_class("main_col")

        yield Label("Options")
        yield Vertical(
            Checkbox("Read after write", id="checkbox_read_after_write"),
            # Button("Show plot", id="btn_show_plot")
        )
        yield Label("Operations")

        yield Label("(placeholder)", id="label_ctn_pollread")
        yield Vertical(
            Checkbox("enabled", id="checkbox_cont_pollread", value=False, disabled=True),
            Label("Poll frequency", id="label_poll_update_frq"),
            RadioSet(
                RadioButton("1 Hz", value=False, id="radio_hz_1"),
                RadioButton("30 Hz", value=True, id="radio_hz_30"),
                RadioButton("100 Hz", value=False, id="radio_hz_100"),
                disabled=True,
                id="radio_set_freq"
            ),
            Label("(placeholder)", id="label_last_poll_update"),
            Label("(never)", id="last_update_time"),
            Label("Avg. update interval"),
            Label("(n/a)", id="update_interval"),
        )

    def update(self) -> None:
        self.app.pushMode = self.app.register is not None and    \
            da.AccessMode.wait_for_new_data in self.app.register.accessor.getAccessModeFlags()

        self.query_one("#label_ctn_pollread", Label).update(
            "Continuous Read" if self.app.pushMode else "Continuous Poll")
        self.query_one("#checkbox_cont_pollread", Checkbox).disabled = not self.app.enableReadButton
        self.query_one("#checkbox_cont_pollread", Checkbox).value = False
        self.app.continuousRead = False

        self.query_one("#label_poll_update_frq", Label).visible = not self.app.pushMode
        self.query_one("#radio_set_freq", RadioSet).visible = not self.app.pushMode
        self.query_one("#radio_set_freq", RadioSet).disabled = True

        self.query_one("#label_last_poll_update", Label).update(
            "Last update time" if self.app.pushMode else "Last poll time")

    def on_mount(self) -> None:
        self.watch(self.app, "register", lambda register: self.update())
        self.watch(self.app, "isOpen", lambda open: self.update())

        self.watch(self.app, "registerValueChanged", lambda old, new: self.on_registerValueChanged(old, new))
        self.watch(self.app, "continuousRead", self.updateRadioSetFrqButtons)
        self.update()

    def updateRadioSetFrqButtons(self) -> None:
        if not self.app.pushMode:
            self.query_one("#radio_set_freq").disabled = not self.app.continuousRead

    def on_registerValueChanged(self, old_time: datetime, new_time: datetime):
        self.query_one("#last_update_time", Label).update(str(new_time))

        if old_time is not None:
            self._avg_update_interval_list.append((new_time - old_time).total_seconds())
            avg = sum(self._avg_update_interval_list) / len(self._avg_update_interval_list)
            self.query_one("#update_interval", Label).update(f"{round(avg * 1000)} ms")

    def on_unmount(self):
        if self.app.pushMode and self.app.register is not None:
            self.app.register.accessor.interrupt()

    @on(Checkbox.Changed, "#checkbox_read_after_write")
    def on_read_after_write_changed(self, changed: Checkbox.Changed):
        self.app.readAfterWrite = changed.control.value

    @on(Checkbox.Changed, "#checkbox_cont_pollread")
    def on_checkbox_changed(self, changed: Checkbox.Changed):
        self.app.continuousRead = changed.control.value

    def on_radio_set_changed(self, changed: RadioSet.Changed) -> None:
        set = self.query_one("#radio_set_freq", RadioSet)
        assert set.pressed_button is not None
        assert set.pressed_button.id is not None
        assert set.pressed_button.id.startswith("radio_hz_")
        hz = int(set.pressed_button.id[9:])
        self.app.continuousPollHz = hz
