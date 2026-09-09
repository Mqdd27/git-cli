from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.containers import Grid, Horizontal, Vertical
from textual.events import Key
from textual.widgets import Button, Footer, Input, Label, ListItem, ListView, RichLog, Static

from git_cli import github, repositories


class CommitScreen(ModalScreen[Optional[str]]):
    CSS = """
    CommitScreen { align: center middle; }
    #commit-dialog { width: 60; height: auto; background: #1c2923; border: tall #d49a3a; padding: 1 2; }
    #commit-message { margin-top: 1; }
    #commit-actions { height: 3; align: center middle; }
    #commit-actions Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="commit-dialog"):
            yield Label("Commit message")
            yield Input(placeholder="Write a commit message", id="commit-message")
            with Horizontal(id="commit-actions"):
                yield Button("Commit", id="confirm-commit")
                yield Button("Cancel", id="cancel-commit")

    def on_mount(self) -> None:
        self.query_one("#commit-message", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-commit":
            self.dismiss(self.query_one("#commit-message", Input).value.strip() or None)
        else:
            self.dismiss(None)


class PushScreen(ModalScreen[Optional[str]]):
    CSS = """
    PushScreen { align: center middle; }
    #push-dialog { width: 60; height: auto; background: #1c2923; border: tall #d49a3a; padding: 1 2; }
    #push-branches { height: 10; margin-top: 1; border: tall #426f58; }
    #push-actions { height: 3; align: center middle; }
    #push-actions Button { margin: 0 1; }
    """

    def __init__(self, branches: list[str]) -> None:
        super().__init__()
        self.branches = branches

    def compose(self) -> ComposeResult:
        with Vertical(id="push-dialog"):
            yield Label("Select a branch to push to origin")
            with ListView(id="push-branches"):
                for branch in self.branches:
                    yield ListItem(Label(branch))
            with Horizontal(id="push-actions"):
                yield Button("Push", id="confirm-push")
                yield Button("Cancel", id="cancel-push")

    def on_mount(self) -> None:
        self.query_one("#push-branches", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(self.selected_branch())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-push":
            self.dismiss(self.selected_branch())
        else:
            self.dismiss(None)

    def selected_branch(self) -> Optional[str]:
        index = self.query_one("#push-branches", ListView).index
        if index is None or index < 0 or index >= len(self.branches):
            return None
        return self.branches[index]


class GitCliApp(App[None]):
    TITLE = "Git CLI"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("g", "refresh_status", "Refresh"),
        ("d", "show_diff", "Diff"),
        ("v", "toggle_visual", "Visual"),
        ("s", "stage_changes", "Stage"),
        ("c", "commit", "Commit"),
        ("p", "push", "Push"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("ctrl+w,h", "focus_repositories", "Repositories"),
        ("ctrl+w,l", "focus_changes", "Changes"),
        ("ctrl+w,j", "focus_diff", "Diff"),
        ("tab", "select_cursor", "Open"),
        ("escape", "show_status", "Status"),
    ]
    CSS = """
    Screen { background: #17201d; color: #e8eadf; }
    Footer, #topbar { background: #24342d; color: #b8c8b9; }
    #topbar { grid-size: 3 1; grid-columns: 1fr auto 1fr; height: 1; padding: 0 1; }
    #title { color: #fff8df; text-align: center; text-style: bold; }
    #github-status { color: #8ed0a8; }
    #repos { width: 30%; background: #203128; border: tall #5fa77a; }
    #content, #setup { width: 70%; background: #1c2923; border: tall #426f58; padding: 1 2; }
    #content { height: 1fr; }
    #repository-title { color: #f5eed8; text-style: bold; }
    #changes { height: 12; margin-top: 1; border: tall #426f58; overflow-y: auto; }
    #changes > ListItem.selected { background: #365f79; color: #fff8df; }
    #diff { height: 1fr; margin-top: 1; color: #f5eed8; border: tall #426f58; }
    ListView > ListItem { padding: 0 1; }
    ListView > ListItem:hover { background: #3a684f; }
    ListView > ListItem.--highlight { background: #d49a3a; color: #1b241f; text-style: bold; }
    Label { color: #d9c48d; text-style: bold; }
    Input { border: tall #5fa77a; background: #142018; color: #f5eed8; }
    Input:focus { border: tall #d49a3a; }
    Button { background: #3a684f; color: #fff8df; border: none; margin-top: 1; }
    Button:hover, Button:focus { background: #d49a3a; color: #1b241f; }
    #import-status { color: #d9c48d; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.repositories = repositories.load()
        self.selected_repository: Optional[Path] = None
        self.changes: list[repositories.Change] = []
        self.selected_change_indexes: set[int] = set()
        self.open_change_indexes: set[int] = set()

    def compose(self) -> ComposeResult:
        with Grid(id="topbar"):
            yield Static(id="github-status")
            yield Static("Git CLI", id="title")
            yield Static()
        with Horizontal():
            yield ListView(id="repos")
            with Vertical(id="content"):
                yield Static("Select a repository to view its status.", id="repository-title")
                yield ListView(id="changes")
                yield RichLog(id="diff", wrap=True)
            with Vertical(id="setup"):
                yield Button("Log in to GitHub", id="github-login")
                yield Label("Import repository file")
                yield Input(placeholder="Path to .txt file", id="repo-file")
                yield Button("Import repositories", id="import-repos")
                yield Static(id="import-status")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_repositories()
        self.show_github_status()
        self.query_one("#setup", Vertical).display = not self.repositories
        self.set_diff("Select changes with v, then press Tab or d to toggle their diffs.")

    def on_key(self, event: Key) -> None:
        if event.key != "tab":
            return
        event.prevent_default()
        event.stop()
        self.action_select_cursor()

    def refresh_repositories(self) -> None:
        repo_list = self.query_one("#repos", ListView)
        repo_list.clear()
        if not self.repositories:
            repo_list.append(ListItem(Label("No repositories yet")))
            return
        for repository in self.repositories:
            repo_list.append(ListItem(Label(repository.name)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "repos":
            index = event.list_view.index
            if index is not None and index < len(self.repositories):
                self.selected_repository = self.repositories[index]
                self.show_status()
        elif event.list_view.id == "changes":
            self.show_diff()

    def show_status(self) -> None:
        if self.selected_repository is None:
            return
        status = repositories.status(self.selected_repository)
        self.changes = status.changes
        self.query_one("#setup", Vertical).display = False
        self.query_one("#repository-title", Static).update(
            f"{self.selected_repository}\nBranch: {status.branch}"
        )
        changes_view = self.query_one("#changes", ListView)
        changes_view.clear()
        if not self.changes:
            changes_view.append(ListItem(Label("Working tree clean.")))
        for change in self.changes:
            changes_view.append(ListItem(Label(f"{change.code} {change.path}")))
        self.selected_change_indexes.clear()
        self.open_change_indexes.clear()
        self.set_diff("Select changes with v, then press Tab or d to toggle their diffs.")

    def show_diff(self) -> None:
        if self.selected_repository is None:
            return
        changes_view = self.query_one("#changes", ListView)
        index = changes_view.index
        if index is None or index < 0 or index >= len(self.changes):
            return
        indexes = self.selected_change_indexes or {index}
        if indexes <= self.open_change_indexes:
            self.open_change_indexes -= indexes
        else:
            self.open_change_indexes |= indexes
        self.render_diffs()

    def render_diffs(self) -> None:
        if not self.open_change_indexes or self.selected_repository is None:
            self.set_diff("Select changes with v, then press Tab or d to toggle their diffs.")
            return
        self.set_diff(
            "\n\n".join(
                repositories.diff(self.selected_repository, self.changes[index])
                for index in sorted(self.open_change_indexes)
            )
        )

    def set_diff(self, content: str) -> None:
        diff_view = self.query_one("#diff", RichLog)
        diff_view.clear()
        diff_view.write(content)

    def action_toggle_visual(self) -> None:
        if self.focused is not self.query_one("#changes", ListView):
            return
        index = self.query_one("#changes", ListView).index
        if index is None or index < 0 or index >= len(self.changes):
            return
        if index in self.selected_change_indexes:
            self.selected_change_indexes.remove(index)
        else:
            self.selected_change_indexes.add(index)
        self.query_one("#changes", ListView).children[index].set_class(
            index in self.selected_change_indexes, "selected"
        )

    def action_refresh_status(self) -> None:
        self.show_status()

    def action_stage_changes(self) -> None:
        if self.selected_repository is None:
            return
        indexes = self.selected_change_indexes or self.current_change_index()
        if not indexes:
            return
        message = repositories.stage(
            self.selected_repository, (self.changes[index] for index in sorted(indexes))
        )
        self.show_status()
        self.set_diff(message)

    def action_commit(self) -> None:
        if self.selected_repository is None:
            return
        self.push_screen(CommitScreen(), self.commit_changes)

    def commit_changes(self, message: Optional[str]) -> None:
        if message is None or self.selected_repository is None:
            return
        result = repositories.commit(self.selected_repository, message)
        self.show_status()
        self.set_diff(result)

    def action_push(self) -> None:
        if self.selected_repository is None:
            return
        branches = repositories.branches(self.selected_repository)
        if not branches:
            self.set_diff("No local branches available to push.")
            return
        self.push_screen(PushScreen(branches), self.push_branch)

    def push_branch(self, branch: Optional[str]) -> None:
        if branch is None or self.selected_repository is None:
            return
        result = repositories.push(self.selected_repository, branch)
        self.show_status()
        self.set_diff(result)

    def current_change_index(self) -> set[int]:
        index = self.query_one("#changes", ListView).index
        if index is None or index < 0 or index >= len(self.changes):
            return set()
        return {index}

    def action_cursor_down(self) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            focused.action_cursor_down()
        elif isinstance(focused, RichLog):
            focused.action_scroll_down()

    def action_cursor_up(self) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            focused.action_cursor_up()
        elif isinstance(focused, RichLog):
            focused.action_scroll_up()

    def action_select_cursor(self) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            focused.action_select_cursor()

    def action_focus_repositories(self) -> None:
        self.query_one("#repos", ListView).focus()

    def action_focus_changes(self) -> None:
        self.query_one("#changes", ListView).focus()

    def action_focus_diff(self) -> None:
        self.query_one("#diff", RichLog).focus()

    def action_show_diff(self) -> None:
        self.show_diff()

    def action_show_status(self) -> None:
        self.show_status()

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
        status.update(f"{len(result.repositories)} repositories added; {len(result.invalid_paths)} invalid paths.")


def main() -> None:
    GitCliApp().run()


if __name__ == "__main__":
    main()
