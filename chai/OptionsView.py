from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Checkbox


class OptionsView(Vertical):

    def compose(self) -> ComposeResult:
        yield Checkbox("Read after write", id="checkbox_read_after_write", value=True)
