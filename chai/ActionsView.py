import asyncio
from textual.app import  ComposeResult
from textual.containers import  Vertical
from textual.widgets import Button, Label, Static, Checkbox, Button, RadioSet, RadioButton

from textual import on, work
from textual.timer import Timer
from textual.worker import get_current_worker

import deviceaccess as da
from datetime import datetime

from chai.DataView import RegisterValueField

from collections import deque


class ActionsView(Vertical):
    _currentRegister: da.GeneralRegisterAccessor | None = None
    _update_timer: Timer | None = None
    _pushMode: bool
    _last_update_time = None
    _avg_update_interval_list: deque = deque(maxlen = 10)

    def compose(self) -> ComposeResult:
        self._pushMode = self._currentRegister is not None and    \
            da.AccessMode.wait_for_new_data in self._currentRegister.getAccessModeFlags()

        self.add_class("main_col")

        yield Label("Options")
        yield Vertical(
                Checkbox("Read after write", id="checkbox_read_after_write"),
                #Button("Show plot", id="btn_show_plot")
            )
        yield Label("Operations")
        yield Vertical(
                Button("Read", disabled=True, id="btn_read"),
                Button("Write", disabled=True, id="btn_write"),
            )
        yield Label("Continous Read" if self._pushMode else "Continous Poll", id="label_ctn_pollread")
        yield Vertical(
                Checkbox("enabled", id="checkbox_cont_pollread"),
                Label("Poll frequency", id="label_poll_update_frq"),
                RadioSet(
                    RadioButton("1 Hz", value=True, id="radio_hz_1"),
                    RadioButton("100 Hz", id="radio_hz_100"),
                    disabled=True,
                    id="radio_set_freq"
                ) if not self._pushMode else Static(),
                Label("Last update time" if self._pushMode else "Last poll time"),
                Label("(never)", id="last_update_time"),
                Label("Avg. update interval"),
                Label("(n/a)", id="update_interval"),
            )

    def changeRegister(self, register: da.GeneralRegisterAccessor):
        if self._update_timer is not None:
            self._update_timer.stop()
            self._update_timer = None

        if self._pushMode and self._currentRegister is not None:
            self._currentRegister.interrupt()

        self._currentRegister = register
        self.refresh(recompose=True)
        self._update_read_write_btn_status()

    def on_unmount(self):
        if self._pushMode and self._currentRegister is not None:
            self._currentRegister.interrupt()

    @on(Button.Pressed, "#btn_read")
    def _pressed_read(self) -> None:
        self._currentRegister.readLatest()
        self.app.query_one(RegisterValueField).update()
        self.query_one("#last_update_time").update(str(datetime.now()))


    @on(Button.Pressed, "#btn_write")
    def _pressed_write(self) -> None:
        self._currentRegister.write()
        if self.query_one("#checkbox_read_after_write").value:
            self.pressed_read()


    def _update_read_write_btn_status(self):
        pollread: Checkbox = self.query_one("#checkbox_cont_pollread")
        if self._currentRegister is not None:
            self.query_one("#btn_read").disabled = (pollread.value or not self._currentRegister.isReadable())
            self.query_one("#btn_write").disabled = (pollread.value or not self._currentRegister.isWriteable())

    @work(exclusive=True, thread=True)
    def _update_push_loop(self) -> None:
        worker = get_current_worker()
        while not worker.is_cancelled:
            try:
                self._currentRegister.read()
            except RuntimeError:
                return
            self.app.call_from_thread(self._update_push_single)

    def _update_push_single(self) -> None:
        now = datetime.now()
        self.query_one("#last_update_time").update(str(now))
        self.app.query_one(RegisterValueField).update()

        if self._last_update_time is not None:
            self._avg_update_interval_list.append((now - self._last_update_time).total_seconds())
            avg = sum(self._avg_update_interval_list) / len(self._avg_update_interval_list)
            self.query_one("#update_interval").update(f"{round(avg*1000)} ms")

        self._last_update_time = now


    @on(Checkbox.Changed, "#checkbox_cont_pollread")
    def on_checkbox_changed(self, changed: Checkbox.Changed):
        self._update_read_write_btn_status()
        if not self._pushMode:
            self.query_one("#radio_set_freq").disabled = not changed.control.value
            self._update_timer_hz()
            if changed.control.value :
                self._update_timer.resume()
            else:
                self._update_timer.pause()
        else :
            if changed.control.value:
                self._update_push_loop()
            else :
                self._currentRegister.interrupt()

    def on_radio_set_changed(self, changed: RadioSet.Changed) -> None:
        self._update_timer_hz()

    def _update_timer_hz(self, pause : bool=False) -> None:
        set = self.query_one("#radio_set_freq", RadioSet)
        if self._update_timer is not None:
            self._update_timer.stop()
        assert set.pressed_button.id.startswith("radio_hz_")
        hz = int(set.pressed_button.id[9:])
        self._update_timer = self.set_interval(1/hz, self._pressed_read, pause=pause)
