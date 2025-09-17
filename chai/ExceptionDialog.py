from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MainApp import LayoutApp
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import Label, Button
from textual import on
from textual.containers import Horizontal


class ExceptionDialog(ModalScreen):
    _exception: RuntimeError
    _title: str
    if TYPE_CHECKING:
        app: LayoutApp

    def __init__(self, title: str, exception: RuntimeError, allowReopen: bool):
        super().__init__()
        self._exception = exception
        self._title = title
        self._allowReopen = allowReopen

    def compose(self) -> ComposeResult:

        yield Grid(
            Label(self._title, id="exception_dialog_title"),
            Label(str(self._exception), id="exception_dialog_message"),
            Label("The device has been closed.", id="exception_dialog_closed_info"),
            Horizontal(
                Button("Ok", variant="primary", id="exception_dialog_ok"),
                Button("Re-open device", id="exception_dialog_reopen", disabled=not self._allowReopen),
                id="execption_dialog_buttons"
            ),
            id="exception_dialog",
        )

    @on(Button.Pressed, "#exception_dialog_ok")
    def pressed_ok(self) -> None:
        self.app.pop_screen()
        self.app.isOpen = False

    @on(Button.Pressed, "#exception_dialog_reopen")
    def pressed_reopen(self) -> None:
        self.app.pop_screen()
        self.app.isOpen = False
        self.app.isOpen = True
