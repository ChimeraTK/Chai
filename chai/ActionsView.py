from textual.app import  ComposeResult
from textual.containers import  Vertical
from textual.widgets import Button, Label, Static, Checkbox, Button, RadioSet, RadioButton

from textual import on
from textual.timer import Timer

import deviceaccess as da

from chai.DataView import RegisterValueField


class ActionsView(Vertical):
    _currentRegister: da.GeneralRegisterAccessor = None
    _update_timer: Timer

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Options"),
            Vertical(
                Checkbox("Read after write", id="checkbox_read_after_write"),
                #Button("Show plot", id="btn_show_plot")
            ),
            Label("Operations"),
            Vertical(
                Button("Read", disabled=True, id="btn_read"),
                Button("Write", disabled=True, id="btn_write"),
            ),
            Label("Continous Poll", id="label_ctn_pollread"),
            Vertical(
                Checkbox("enabled", id="checkbox_cont_pollread"),
                Label("Poll frequency", id="label_poll_update_frq"),
                RadioSet(
                    RadioButton("1 Hz", value=True, id="radio_1hz"),
                    RadioButton("100 Hz", id="radio_100hz"),
                    disabled=True,
                    id="radio_set_freq"
                ),
                Label("Last poll time"),
                Static("2024-06-25T13:14:15.452"),
                Label("Avg. update interval"),
                Static(""),

            ),
            id="options",
            classes="main_col")

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self._update_timer = self.set_interval(1, self._pressed_read, pause=True)

    def changeRegister(self, register: da.GeneralRegisterAccessor):
      self._currentRegister = register
      self._update_read_write_btn_status()


    @on(Button.Pressed, "#btn_read")
    def _pressed_read(self) -> None:
        self._currentRegister.readLatest()
        self.app.query_one(RegisterValueField).update()


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
            if pollread.value:
                self._update_timer.resume()
            else:
                self._update_timer.pause()

    def on_checkbox_changed(self, changed: Checkbox.Changed):
        if changed.control.id == "checkbox_cont_pollread":
            self._update_read_write_btn_status()
            self.query_one("#radio_set_freq").disabled = changed.control.value


    def on_radio_set_changed(self, changed: RadioSet.Changed) -> None:
        if changed.pressed.id == "radio_1hz":
            self.set_interval(1, self.update, pause=True)
        if changed.pressed.id == "radio_100hz":
            self.set_interval(1/100, self.update, pause=True)
