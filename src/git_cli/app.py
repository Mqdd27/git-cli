from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static


class GitCliApp(App[None]):
    TITLE = "Git CLI"
    CSS = """
    #repos {
        width: 30%;
        border: solid $primary;
    }

    #details {
        width: 70%;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ListView(id="repos")
            yield Static("Tambahkan repository untuk mulai memantau.", id="details")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ListView).append(ListItem(Label("Belum ada repository")))


def main() -> None:
    GitCliApp().run()


if __name__ == "__main__":
    main()
