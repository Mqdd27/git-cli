from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from git_cli import github, repositories


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

    #github-login, #import-repos {
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.repositories = repositories.load()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ListView(id="repos")
            with Vertical(id="details"):
                yield Static("Select a repository to view its status.", id="repository-details")
                yield Static(id="github-status")
                yield Button("Log in to GitHub", id="github-login")
                yield Label("Import repository file")
                yield Input(placeholder="Path to .txt file", id="repo-file")
                yield Button("Import repositories", id="import-repos")
                yield Static(id="import-status")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_repositories()
        self.show_github_status()

    def refresh_repositories(self) -> None:
        repo_list = self.query_one(ListView)
        repo_list.clear()
        if not self.repositories:
            repo_list.append(ListItem(Label("No repositories yet")))
            return
        for index, repository in enumerate(self.repositories):
            repo_list.append(ListItem(Label(repository.name), id=f"repository-{index}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id is None or not item_id.startswith("repository-"):
            return
        repository = self.repositories[int(item_id.removeprefix("repository-"))]
        repository_status = repositories.status(repository)
        self.query_one("#repository-details", Static).update(
            f"{repository}\n\nBranch: {repository_status.branch}\n\n{repository_status.changes}"
        )

    def show_github_status(self) -> None:
        github_status = github.status()
        self.query_one("#github-status", Static).update(github_status.message)
        self.query_one("#github-login", Button).display = (
            github_status.available and not github_status.authenticated
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "github-login":
            with self.suspend():
                github.login()
            self.show_github_status()
        elif event.button.id == "import-repos":
            self.import_repositories()

    def import_repositories(self) -> None:
        status = self.query_one("#import-status", Static)
        file_name = self.query_one("#repo-file", Input).value.strip()
        if not file_name:
            status.update("Enter a repository file path.")
            return

        path = Path(file_name).expanduser()
        if not path.is_file():
            status.update("File not found.")
            return

        result = repositories.import_file(path, self.repositories)
        self.repositories.extend(result.repositories)
        repositories.save(self.repositories)
        self.refresh_repositories()
        status.update(
            f"{len(result.repositories)} repositories added; "
            f"{len(result.invalid_paths)} invalid paths."
        )


def main() -> None:
    GitCliApp().run()


if __name__ == "__main__":
    main()
