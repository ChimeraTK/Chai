from textual.app import App, ComposeResult
from textual.widgets import Button, ListView, ListItem, Label, Static


class DeviceView(ListView):

    def appendItem(self, text: str) -> None:
        self.append(ListItem(Label(text)))


class AppendDeviceApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Static("Yo", id="yo")
        yield Button("Add device")

    def on_button_pressed(self) -> None:
        dv = self.query_one("#yo")
        dv.update("Some more item")


AppendDeviceApp().run()
