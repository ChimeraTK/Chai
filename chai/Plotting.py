from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer
from textual import events
from textual_plotext import PlotextPlot


class PlotScreen(Screen):
    """Screen with a plot of current Register content."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield PlotextPlot()
        yield Footer()

    def on_mount(self) -> None:
        plt = self.query_one(PlotextPlot).plt
        y = plt.sin()
        plt.scatter(y)
        plt.title("Scatter Plot")  # to apply a title

    def on_key(self, event: events.Key) -> None:
        print(event.key)
        if event.name == "escape":
            self.app.pop_screen()
