import os
from pathlib import Path
import shlex
import subprocess
from typing import Optional

from textual.app import App, ComposeResult, SystemCommand
from textual.command import CommandPalette
from textual.screen import ModalScreen
from textual.containers import Grid, Horizontal, Vertical
from textual.events import Key
from textual.widgets import Button, Footer, Input, Label, ListItem, ListView, RichLog, Static

from git_cli import github, repositories


class CommitScreen(ModalScreen[Optional[str]]):
    CSS = """
    CommitScreen { align: center middle; }
    #commit-dialog { width: 60; height: auto; padding: 1 2; }
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
    #push-dialog { width: 60; height: auto; padding: 1 2; }
    #push-branches { height: 10; margin-top: 1;  }
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


class UndoCommitScreen(ModalScreen[bool]):
    CSS = """
    UndoCommitScreen { align: center middle; }
    #undo-dialog { width: 70; height: auto; padding: 1 2; }
    #undo-actions { height: 3; align: center middle; }
    #undo-actions Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="undo-dialog"):
            yield Label("Undo the last commit?")
            yield Static("The commit is removed locally. Its changes remain staged. Pushed commits are not reverted remotely.")
            with Horizontal(id="undo-actions"):
                yield Button("Undo commit", id="confirm-undo")
                yield Button("Cancel", id="cancel-undo")

    def on_mount(self) -> None:
        self.query_one("#cancel-undo", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-undo")


class DiscardScreen(ModalScreen[bool]):
    CSS = """
    DiscardScreen { align: center middle; }
    #discard-dialog { width: 70; height: auto; padding: 1 2; }
    #discard-actions { height: 3; align: center middle; }
    #discard-actions Button { margin: 0 1; }
    """

    def __init__(self, count: int) -> None:
        super().__init__()
        self.count = count

    def compose(self) -> ComposeResult:
        with Vertical(id="discard-dialog"):
            yield Label(f"Discard changes in {self.count} selected file(s)?")
            yield Static("This cannot be undone. Untracked files are not deleted.")
            with Horizontal(id="discard-actions"):
                yield Button("Discard changes", id="confirm-discard")
                yield Button("Cancel", id="cancel-discard")

    def on_mount(self) -> None:
        self.query_one("#cancel-discard", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-discard")


class PullStrategyScreen(ModalScreen[Optional[bool]]):
    CSS = """
    PullStrategyScreen { align: center middle; }
    #pull-dialog { width: 70; height: auto; padding: 1 2; }
    #pull-actions { height: 3; align: center middle; }
    #pull-actions Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="pull-dialog"):
            yield Label("Remote and local branches have diverged")
            yield Static("Choose how to integrate remote commits. No rebase is the default.")
            with Horizontal(id="pull-actions"):
                yield Button("Pull without rebase", id="pull-merge")
                yield Button("Pull with rebase", id="pull-rebase")
                yield Button("Cancel", id="cancel-pull")

    def on_mount(self) -> None:
        self.query_one("#pull-merge", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pull-merge":
            self.dismiss(False)
        elif event.button.id == "pull-rebase":
            self.dismiss(True)
        else:
            self.dismiss(None)


class ConfirmCloseScreen(ModalScreen[bool]):
    CSS = """
    ConfirmCloseScreen { align: center middle; }
    #close-dialog { width: 60; height: auto; padding: 1 2; }
    #close-actions { height: 3; align: center middle; }
    #close-actions Button { margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="close-dialog"):
            yield Label("Close this GitHub issue?")
            yield Static("This changes the issue state on GitHub.")
            with Horizontal(id="close-actions"):
                yield Button("Close issue", id="confirm-close")
                yield Button("Cancel", id="cancel-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-close")


class IssueDetailScreen(ModalScreen[None]):
    CSS = """
    IssueDetailScreen { align: center middle; }
    #issue-dialog { width: 100; height: 32; padding: 1 2; }
    #issue-content { height: 1fr; margin-top: 1;  }
    #issue-actions { height: 3; }
    #issue-actions Button { margin: 0 1; }
    """

    def __init__(self, repository: str, issue_number: int) -> None:
        super().__init__()
        self.repository = repository
        self.issue_number = issue_number

    def compose(self) -> ComposeResult:
        with Vertical(id="issue-dialog"):
            yield Static("Loading issue...", id="issue-title")
            yield RichLog(id="issue-content", wrap=True)
            with Horizontal(id="issue-actions"):
                yield Button("Reply", id="reply-issue")
                yield Button("Close issue", id="close-issue")
                yield Button("Back", id="back-issue")

    def on_mount(self) -> None:
        self.refresh_issue()

    def refresh_issue(self) -> None:
        issue, message = github.issue(self.repository, self.issue_number)
        content = self.query_one("#issue-content", RichLog)
        content.clear()
        if issue is None:
            self.query_one("#issue-title", Static).update(message)
            return
        self.query_one("#issue-title", Static).update(f"#{issue.number} [{issue.state}] {issue.title}")
        content.write(issue.body or "No description.")
        for comment in issue.comments:
            content.write("\n---\n" + comment)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reply-issue":
            self.app.push_themed_screen(CommitScreen(), self.add_comment)
        elif event.button.id == "close-issue":
            self.app.push_themed_screen(ConfirmCloseScreen(), self.close_issue)
        else:
            self.dismiss()

    def add_comment(self, message: Optional[str]) -> None:
        if message:
            result = github.comment(self.repository, self.issue_number, message)
            self.query_one("#issue-content", RichLog).write("\n" + result)
            self.refresh_issue()

    def close_issue(self, confirmed: bool) -> None:
        if confirmed:
            result = github.close(self.repository, self.issue_number)
            self.query_one("#issue-content", RichLog).write("\n" + result)
            self.refresh_issue()


class IssuesScreen(ModalScreen[None]):
    CSS = """
    IssuesScreen { align: center middle; }
    #issues-dialog { width: 80; height: 24; padding: 1 2; }
    #issues-list { height: 1fr; margin-top: 1;  }
    """

    def __init__(self, repository: str, issues: list[github.Issue], message: str) -> None:
        super().__init__()
        self.repository = repository
        self.issues = issues
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="issues-dialog"):
            yield Label("GitHub issues")
            if self.message:
                yield Static(self.message)
            elif not self.issues:
                yield Static("No open issues.")
            else:
                with ListView(id="issues-list"):
                    for issue in self.issues:
                        yield ListItem(Label(f"#{issue.number} [{issue.state}] {issue.title}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        if index is not None and index < len(self.issues):
            self.app.push_themed_screen(IssueDetailScreen(self.repository, self.issues[index].number))

    def on_key(self, event: Key) -> None:
        if event.key in ("escape", "q"):
            event.stop()
            self.dismiss()


class ThemeScreen(ModalScreen[Optional[str]]):
    CSS = """
    ThemeScreen { align: center middle; }
    #theme-dialog { width: 60; height: auto; padding: 1 2; }
    #theme-list { height: 8; margin-top: 1;  }
    """

    def __init__(self, themes: list[tuple[str, str]]) -> None:
        super().__init__()
        self.themes = themes

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-dialog"):
            yield Label("Select theme")
            with ListView(id="theme-list"):
                for _, label in self.themes:
                    yield ListItem(Label(label))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        self.dismiss(self.themes[index][0] if index is not None else None)

    def on_key(self, event: Key) -> None:
        if event.key in ("escape", "q"):
            event.stop()
            self.dismiss(None)


class GitCliApp(App[None]):
    TITLE = "Git CLI"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("g", "refresh_status", "Refresh"),
        ("d", "show_diff", "Diff"),
        ("v", "toggle_visual", "Visual"),
        ("s", "stage_changes", "Stage"),
        ("c", "commit", "Commit"),
        ("u", "undo_commit", "Undo commit"),
        ("p", "push", "Push"),
        ("P", "pull", "Pull"),
        ("i", "issues", "Issues"),
        ("o", "open_changes", "Open editor"),
        ("T", "theme", "Theme"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("ctrl+w", "window_prefix", "Window"),
        ("tab", "select_cursor", "Open"),
        ("escape", "show_status", "Status"),
    ]
    CSS = """
    Screen { background: #17201d; color: #e8eadf; }
    Footer, #topbar { background: #24342d; color: #b8c8b9; }
    #topbar { grid-size: 3 1; grid-columns: 1fr auto 1fr; height: 1; padding: 0 1; }
    #title { color: #fff8df; text-align: center; text-style: bold; }
    #github-status { color: #8ed0a8; }
    #repos { width: 30%; background: #203128; border: tall #5fa77a; color: #e8eadf; }
    #content, #setup { width: 70%; background: #1c2923; border: tall #426f58; padding: 1 2; color: #e8eadf; }
    #content { height: 1fr; }
    #repository-title { color: #f5eed8; text-style: bold; }
    #changes { height: 12; margin-top: 1; border: tall #426f58; overflow-y: auto; background: #1c2923; color: #e8eadf; }
    #changes > ListItem.selected { background: #365f79; color: #fff8df; }
    #diff { height: 1fr; margin-top: 1; color: #f5eed8; border: tall #426f58; background: #1c2923; }
    #diff:focus { border: tall #d49a3a; background: #142018; }
    ListView > ListItem { padding: 0 1; }
    ListView > ListItem:hover { background: #3a684f; color: #fff8df; }
    ListView > ListItem.--highlight { background: #d49a3a; color: #1b241f; text-style: bold; }
    Label { color: #d9c48d; text-style: bold; }
    Input { border: tall #5fa77a; background: #142018; color: #f5eed8; }
    Input:focus { border: tall #d49a3a; }
    Button { background: #3a684f; color: #fff8df; border: none; margin-top: 1; }
    Button:hover, Button:focus { background: #d49a3a; color: #1b241f; }
    #import-status { color: #d9c48d; }

    .modal--forest > * { background: #1c2923; border: tall #d49a3a; }
    .modal--forest ListView, .modal--forest RichLog { background: #1c2923; border: tall #426f58; }

    CommandPalette.palette--forest, CommandPalette.palette--forest > Vertical { background: #1c2923; color: #e8eadf; }
    CommandPalette.palette--forest #--input, CommandPalette.palette--forest #--results { background: #142018; border: tall #d49a3a; color: #f5eed8; }

    Screen.midnight { background: #111827; color: #dbeafe; }
    Screen.midnight Footer, Screen.midnight #topbar { background: #1e293b; color: #94a3b8; }
    Screen.midnight #title, Screen.midnight #repository-title { color: #e2e8f0; }
    Screen.midnight #github-status { color: #60a5fa; }
    Screen.midnight #repos { background: #172554; border: tall #38bdf8; color: #dbeafe; }
    Screen.midnight #content, Screen.midnight #setup { background: #172033; border: tall #475569; color: #dbeafe; }
    Screen.midnight #changes, Screen.midnight #diff { background: #0f172a; border: tall #475569; color: #dbeafe; }
    Screen.midnight #diff:focus { border: tall #f59e0b; background: #111827; }
    Screen.midnight ListView > ListItem:hover, Screen.midnight Button { background: #1d4ed8; color: #ffffff; }
    Screen.midnight ListView > ListItem.--highlight, Screen.midnight Button:hover, Screen.midnight Button:focus { background: #f59e0b; color: #111827; }
    Screen.midnight Input { background: #0f172a; border: tall #38bdf8; color: #dbeafe; }
    Screen.midnight Input:focus { border: tall #f59e0b; }
    Screen.midnight Label, Screen.midnight #import-status { color: #fde68a; }
    Screen.midnight #changes > ListItem.selected { background: #1e3a5f; color: #dbeafe; }

    .modal--midnight { background: #172033; color: #dbeafe; }
    .modal--midnight > * { background: #172033; border: tall #38bdf8; color: #dbeafe; }
    .modal--midnight ListView, .modal--midnight RichLog { background: #0f172a; border: tall #475569; color: #dbeafe; }
    .modal--midnight ListView > ListItem:hover, .modal--midnight Button { background: #1d4ed8; color: #ffffff; }
    .modal--midnight ListView > ListItem.--highlight, .modal--midnight Button:hover, .modal--midnight Button:focus { background: #f59e0b; color: #111827; }
    .modal--midnight Input { background: #0f172a; border: tall #38bdf8; color: #dbeafe; }
    .modal--midnight Input:focus { border: tall #f59e0b; }
    .modal--midnight Label { color: #fde68a; }
    CommandPalette.palette--midnight, CommandPalette.palette--midnight > Vertical { background: #172033; color: #dbeafe; }
    CommandPalette.palette--midnight #--input, CommandPalette.palette--midnight #--results { background: #0f172a; border: tall #38bdf8; color: #dbeafe; }

    Screen.light { background: #f8fafc; color: #1e293b; }
    Screen.light Footer, Screen.light #topbar { background: #e2e8f0; color: #475569; }
    Screen.light #title, Screen.light #repository-title { color: #0f172a; }
    Screen.light #github-status { color: #4f46e5; }
    Screen.light #repos { background: #f1f5f9; border: tall #2563eb; color: #1e293b; }
    Screen.light #content, Screen.light #setup { background: #ffffff; border: tall #cbd5e1; color: #1e293b; }
    Screen.light #changes, Screen.light #diff { background: #ffffff; border: tall #cbd5e1; color: #1e293b; }
    Screen.light #diff:focus { border: tall #d97706; background: #fff7ed; }
    Screen.light ListView > ListItem:hover, Screen.light Button { background: #2563eb; color: #ffffff; }
    Screen.light ListView > ListItem.--highlight, Screen.light Button:hover, Screen.light Button:focus { background: #d97706; color: #ffffff; }
    Screen.light Input { background: #ffffff; border: tall #2563eb; color: #1e293b; }
    Screen.light Input:focus { border: tall #d97706; }
    Screen.light Label, Screen.light #import-status { color: #92400e; }
    Screen.light #changes > ListItem.selected { background: #dbeafe; color: #1e3a8a; }

    .modal--light { background: #ffffff; color: #1e293b; }
    .modal--light > * { background: #ffffff; border: tall #2563eb; color: #1e293b; }
    .modal--light ListView, .modal--light RichLog { background: #f8fafc; border: tall #cbd5e1; color: #1e293b; }
    .modal--light ListView > ListItem:hover, .modal--light Button { background: #2563eb; color: #ffffff; }
    .modal--light ListView > ListItem.--highlight, .modal--light Button:hover, .modal--light Button:focus { background: #d97706; color: #ffffff; }
    .modal--light Input { background: #ffffff; border: tall #2563eb; color: #1e293b; }
    .modal--light Input:focus { border: tall #d97706; }
    .modal--light Label { color: #92400e; }
    CommandPalette.palette--light, CommandPalette.palette--light > Vertical { background: #ffffff; color: #1e293b; }
    CommandPalette.palette--light #--input, CommandPalette.palette--light #--results { background: #f8fafc; border: tall #2563eb; color: #1e293b; }

    Screen.rose-pine { background: #191724; color: #e0def4; }
    Screen.rose-pine Footer, Screen.rose-pine #topbar { background: #26233a; color: #908caa; }
    Screen.rose-pine #title, Screen.rose-pine #repository-title { color: #e0def4; }
    Screen.rose-pine #github-status { color: #9ccfd8; }
    Screen.rose-pine #repos { background: #1f1d2e; border: tall #c4a7e7; color: #e0def4; }
    Screen.rose-pine #content, Screen.rose-pine #setup { background: #1f1d2e; border: tall #403d52; color: #e0def4; }
    Screen.rose-pine #changes, Screen.rose-pine #diff { background: #191724; border: tall #403d52; color: #e0def4; }
    Screen.rose-pine #diff:focus { border: tall #ebbcba; background: #26233a; }
    Screen.rose-pine ListView > ListItem:hover, Screen.rose-pine Button { background: #403d52; color: #e0def4; }
    Screen.rose-pine ListView > ListItem.--highlight, Screen.rose-pine Button:hover, Screen.rose-pine Button:focus { background: #c4a7e7; color: #191724; }
    Screen.rose-pine Input { background: #191724; border: tall #9ccfd8; color: #e0def4; }
    Screen.rose-pine Input:focus { border: tall #ebbcba; }
    Screen.rose-pine Label, Screen.rose-pine #import-status { color: #f6c177; }
    Screen.rose-pine #changes > ListItem.selected { background: #524f67; color: #e0def4; }

    .modal--rose-pine { background: #1f1d2e; color: #e0def4; }
    .modal--rose-pine > * { background: #1f1d2e; border: tall #c4a7e7; color: #e0def4; }
    .modal--rose-pine ListView, .modal--rose-pine RichLog { background: #191724; border: tall #403d52; color: #e0def4; }
    .modal--rose-pine ListView > ListItem:hover, .modal--rose-pine Button { background: #403d52; color: #e0def4; }
    .modal--rose-pine ListView > ListItem.--highlight, .modal--rose-pine Button:hover, .modal--rose-pine Button:focus { background: #c4a7e7; color: #191724; }
    .modal--rose-pine Input { background: #191724; border: tall #9ccfd8; color: #e0def4; }
    .modal--rose-pine Input:focus { border: tall #ebbcba; }
    .modal--rose-pine Label { color: #f6c177; }
    CommandPalette.palette--rose-pine, CommandPalette.palette--rose-pine > Vertical { background: #1f1d2e; color: #e0def4; }
    CommandPalette.palette--rose-pine #--input, CommandPalette.palette--rose-pine #--results { background: #191724; border: tall #c4a7e7; color: #e0def4; }

    Screen.catppuccin { background: #1e1e2e; color: #cdd6f4; }
    Screen.catppuccin Footer, Screen.catppuccin #topbar { background: #181825; color: #a6adc8; }
    Screen.catppuccin #title, Screen.catppuccin #repository-title { color: #cdd6f4; }
    Screen.catppuccin #github-status { color: #94e2d5; }
    Screen.catppuccin #repos { background: #181825; border: tall #cba6f7; color: #cdd6f4; }
    Screen.catppuccin #content, Screen.catppuccin #setup { background: #181825; border: tall #45475a; color: #cdd6f4; }
    Screen.catppuccin #changes, Screen.catppuccin #diff { background: #1e1e2e; border: tall #45475a; color: #cdd6f4; }
    Screen.catppuccin #diff:focus { border: tall #f9e2af; background: #313244; }
    Screen.catppuccin ListView > ListItem:hover, Screen.catppuccin Button { background: #45475a; color: #cdd6f4; }
    Screen.catppuccin ListView > ListItem.--highlight, Screen.catppuccin Button:hover, Screen.catppuccin Button:focus { background: #cba6f7; color: #1e1e2e; }
    Screen.catppuccin Input { background: #1e1e2e; border: tall #94e2d5; color: #cdd6f4; }
    Screen.catppuccin Input:focus { border: tall #f9e2af; }
    Screen.catppuccin Label, Screen.catppuccin #import-status { color: #f9e2af; }
    Screen.catppuccin #changes > ListItem.selected { background: #585b70; color: #cdd6f4; }

    .modal--catppuccin { background: #181825; color: #cdd6f4; }
    .modal--catppuccin > * { background: #181825; border: tall #cba6f7; color: #cdd6f4; }
    .modal--catppuccin ListView, .modal--catppuccin RichLog { background: #1e1e2e; border: tall #45475a; color: #cdd6f4; }
    .modal--catppuccin ListView > ListItem:hover, .modal--catppuccin Button { background: #45475a; color: #cdd6f4; }
    .modal--catppuccin ListView > ListItem.--highlight, .modal--catppuccin Button:hover, .modal--catppuccin Button:focus { background: #cba6f7; color: #1e1e2e; }
    .modal--catppuccin Input { background: #1e1e2e; border: tall #94e2d5; color: #cdd6f4; }
    .modal--catppuccin Input:focus { border: tall #f9e2af; }
    .modal--catppuccin Label { color: #f9e2af; }
    CommandPalette.palette--catppuccin, CommandPalette.palette--catppuccin > Vertical { background: #181825; color: #cdd6f4; }
    CommandPalette.palette--catppuccin #--input, CommandPalette.palette--catppuccin #--results { background: #1e1e2e; border: tall #cba6f7; color: #cdd6f4; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.repositories = repositories.load()
        self.custom_themes = {theme.name: theme for theme in repositories.custom_themes()}
        self.color_theme = repositories.load_theme()
        self.selected_repository: Optional[Path] = None
        self.changes: list[repositories.Change] = []
        self.selected_change_indexes: set[int] = set()
        self.open_change_indexes: set[int] = set()
        self.awaiting_window_command = False
        self.awaiting_diff_g = False
        self.awaiting_changes_d = False

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

    def get_system_commands(self, screen: object) -> object:
        for command in super().get_system_commands(screen):
            if command.title != "Change theme":
                yield command
        yield SystemCommand("Refresh repositories", "Read repos.txt and refresh Git status", self.action_refresh_status)
        yield SystemCommand("Stage selected changes", "Stage or unstage the selected changed files", self.action_stage_changes)
        yield SystemCommand("Commit staged changes", "Write a commit message", self.action_commit)
        yield SystemCommand("Undo last commit", "Undo the latest local commit and keep changes staged", self.action_undo_commit)
        yield SystemCommand("Pull active branch", "Pull with fast-forward, merge, or rebase", self.action_pull)
        yield SystemCommand("Push branch", "Select a local branch to push to origin", self.action_push)
        yield SystemCommand("View GitHub issues", "Open issues for the active repository", self.action_issues)
        yield SystemCommand("Change color theme", "Select Forest, Midnight, Light, Rosé Pine, or Catppuccin", self.action_theme)

    def action_command_palette(self) -> None:
        palette = CommandPalette(id="--command-palette")
        palette.add_class(f"palette--{self.color_theme}")
        self.push_screen(palette)

    def on_mount(self) -> None:
        self.load_custom_theme_styles()
        self.apply_theme(self.color_theme)
        self.sync_source_file()
        self.refresh_repositories()
        self.show_github_status()
        self.query_one("#setup", Vertical).display = not self.repositories
        self.set_diff("Select changes with v, then press Tab or d to toggle their diffs.")

    def on_key(self, event: Key) -> None:
        if self.awaiting_changes_d:
            self.awaiting_changes_d = False
            event.prevent_default()
            event.stop()
            if event.key == "d":
                self.action_discard_changes()
            return
        if isinstance(self.focused, ListView) and self.focused.id == "changes" and event.key == "d":
            event.prevent_default()
            event.stop()
            self.awaiting_changes_d = True
            return
        if isinstance(self.focused, RichLog):
            if event.key == "ctrl+d":
                event.prevent_default()
                event.stop()
                self.focused.action_page_down()
                return
            if event.key == "ctrl+u":
                event.prevent_default()
                event.stop()
                self.focused.action_page_up()
                return
            if event.key == "G":
                event.prevent_default()
                event.stop()
                self.awaiting_diff_g = False
                self.focused.action_scroll_end()
                return
            if self.awaiting_diff_g:
                self.awaiting_diff_g = False
                event.prevent_default()
                event.stop()
                if event.key == "g":
                    self.focused.action_scroll_home()
                return
            if event.key == "g":
                event.prevent_default()
                event.stop()
                self.awaiting_diff_g = True
                return
        if self.awaiting_window_command:
            self.awaiting_window_command = False
            event.prevent_default()
            event.stop()
            if event.key == "h":
                self.action_focus_repositories()
            elif event.key in ("l", "k"):
                self.action_focus_changes()
            elif event.key == "j":
                self.action_focus_diff()
            return
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
        selected_path = self.current_change_path()
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
        if selected_path:
            for index, change in enumerate(self.changes):
                if change.path == selected_path:
                    changes_view.index = index
                    break
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
        self.sync_source_file()
        self.show_status()

    def action_discard_changes(self) -> None:
        if self.selected_repository is None:
            return
        indexes = self.selected_change_indexes or self.current_change_index()
        if not indexes:
            return
        self.push_themed_screen(DiscardScreen(len(indexes)), lambda confirmed: self.discard_changes(indexes, confirmed))

    def discard_changes(self, indexes: set[int], confirmed: bool) -> None:
        if not confirmed or self.selected_repository is None:
            return
        result = repositories.discard(
            self.selected_repository, (self.changes[index] for index in sorted(indexes))
        )
        self.show_status()
        self.set_diff(result)

    def action_open_changes(self) -> None:
        if self.selected_repository is None or self.focused is not self.query_one("#changes", ListView):
            return
        indexes = self.selected_change_indexes or self.current_change_index()
        if not indexes:
            return
        files = [self.changes[index].path for index in sorted(indexes)]
        editor = shlex.split(os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi")
        with self.suspend():
            subprocess.call([*editor, *files], cwd=self.selected_repository)
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
        self.push_themed_screen(CommitScreen(), self.commit_changes)

    def commit_changes(self, message: Optional[str]) -> None:
        if message is None or self.selected_repository is None:
            return
        result = repositories.commit(self.selected_repository, message)
        self.show_status()
        self.set_diff(result)

    def push_themed_screen(self, screen: ModalScreen, callback: object = None) -> None:
        screen.add_class(f"modal--{self.color_theme}")
        self.push_screen(screen, callback)

    def load_custom_theme_styles(self) -> None:
        for theme in self.custom_themes.values():
            colors = theme.colors
            selector = f"custom-{theme.name}"
            css = f"""
            Screen.{selector}, .modal--{selector} {{ background: {colors['background']}; color: {colors['text']}; }}
            Screen.{selector} #topbar, Screen.{selector} Footer {{ background: {colors['surface']}; color: {colors['muted']}; }}
            Screen.{selector} #repos, Screen.{selector} #content, Screen.{selector} #setup {{ background: {colors['surface']}; border: tall {colors['border']}; color: {colors['text']}; }}
            Screen.{selector} #changes, Screen.{selector} #diff {{ background: {colors['surface_alt']}; border: tall {colors['border']}; color: {colors['text']}; }}
            Screen.{selector} #diff:focus {{ border: tall {colors['highlight']}; background: {colors['surface']}; }}
            Screen.{selector} ListView > ListItem:hover, Screen.{selector} Button {{ background: {colors['accent']}; color: {colors['background']}; }}
            Screen.{selector} ListView > ListItem.--highlight, Screen.{selector} Button:hover, Screen.{selector} Button:focus {{ background: {colors['highlight']}; color: {colors['background']}; }}
            Screen.{selector} Input {{ background: {colors['surface_alt']}; border: tall {colors['accent']}; color: {colors['text']}; }}
            Screen.{selector} Label {{ color: {colors['label']}; }}
            Screen.{selector} #github-status {{ color: {colors['accent']}; }}
            .modal--{selector} > * {{ background: {colors['surface']}; border: tall {colors['accent']}; color: {colors['text']}; }}
            .modal--{selector} ListView, .modal--{selector} RichLog, .modal--{selector} Input {{ background: {colors['surface_alt']}; border: tall {colors['border']}; color: {colors['text']}; }}
            .modal--{selector} ListView > ListItem:hover, .modal--{selector} Button {{ background: {colors['accent']}; color: {colors['background']}; }}
            .modal--{selector} ListView > ListItem.--highlight, .modal--{selector} Button:hover, .modal--{selector} Button:focus {{ background: {colors['highlight']}; color: {colors['background']}; }}
            .modal--{selector} Label {{ color: {colors['label']}; }}
            CommandPalette.palette--{selector}, CommandPalette.palette--{selector} > Vertical {{ background: {colors['surface']}; color: {colors['text']}; }}
            CommandPalette.palette--{selector} #--input, CommandPalette.palette--{selector} #--results {{ background: {colors['surface_alt']}; border: tall {colors['accent']}; color: {colors['text']}; }}
            """
            self.stylesheet.add_source(css)
        self.stylesheet.reparse()
        self.stylesheet.update(self.screen)

    def action_theme(self) -> None:
        builtins = [("forest", "Forest"), ("midnight", "Midnight"), ("light", "Light"), ("rose-pine", "Rosé Pine"), ("catppuccin", "Catppuccin Mocha")]
        custom = [(f"custom-{theme.name}", theme.label) for theme in self.custom_themes.values()]
        self.push_themed_screen(ThemeScreen(builtins + custom), self.apply_theme)

    def apply_theme(self, theme: Optional[str]) -> None:
        valid_themes = {"forest", "midnight", "light", "rose-pine", "catppuccin"}
        valid_themes.update(f"custom-{name}" for name in self.custom_themes)
        if theme not in valid_themes:
            return
        self.screen.remove_class("midnight", "light", "rose-pine", "catppuccin", *[f"custom-{name}" for name in self.custom_themes])
        if theme != "forest":
            self.screen.add_class(theme)
        self.color_theme = theme
        repositories.save_theme(theme)

    def action_undo_commit(self) -> None:
        if self.selected_repository is None:
            return
        self.push_themed_screen(UndoCommitScreen(), self.undo_commit)

    def undo_commit(self, confirmed: bool) -> None:
        if not confirmed or self.selected_repository is None:
            return
        result = repositories.undo_last_commit(self.selected_repository)
        self.show_status()
        self.set_diff(result)

    def action_pull(self) -> None:
        if self.selected_repository is None:
            return
        self.set_diff("Preparing fast-forward pull...\n\nRunning: git pull --ff-only")
        self.call_after_refresh(self.run_fast_forward_pull)

    def run_fast_forward_pull(self) -> None:
        if self.selected_repository is None:
            return
        completed, result = repositories.pull_fast_forward(self.selected_repository)
        if completed:
            self.show_status()
            self.set_diff(f"Pull result\n\n{result}")
            return
        self.set_diff(f"Fast-forward pull was not possible.\n\n{result}")
        self.push_themed_screen(PullStrategyScreen(), self.run_pull_strategy)

    def run_pull_strategy(self, rebase: Optional[bool]) -> None:
        if rebase is None or self.selected_repository is None:
            return
        command = "git pull --rebase" if rebase else "git pull --no-rebase"
        self.set_diff(f"Preparing pull...\n\nRunning: {command}")
        self.call_after_refresh(self.execute_pull_strategy, rebase)

    def execute_pull_strategy(self, rebase: bool) -> None:
        if self.selected_repository is None:
            return
        completed, result = repositories.pull(self.selected_repository, rebase)
        self.show_status()
        if completed:
            self.set_diff(f"Pull completed\n\n{result}")
            return
        self.set_diff(f"Pull stopped; resolve conflicts before continuing.\n\n{result}")
        self.open_conflict_editor()

    def open_conflict_editor(self) -> None:
        if self.selected_repository is None:
            return
        files = repositories.conflicted_files(self.selected_repository)
        if not files:
            return
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
        with self.suspend():
            subprocess.call([editor, *files], cwd=self.selected_repository)

    def action_issues(self) -> None:
        if self.selected_repository is None:
            return
        github_repository = repositories.github_repository(self.selected_repository)
        if not github_repository:
            self.push_themed_screen(IssuesScreen("", [], "Repository has no GitHub origin remote."))
            return
        issue_list, message = github.issues(github_repository)
        self.push_themed_screen(IssuesScreen(github_repository, issue_list, message))

    def action_push(self) -> None:
        if self.selected_repository is None:
            return
        branches = repositories.branches(self.selected_repository)
        if not branches:
            self.set_diff("No local branches available to push.")
            return
        self.push_themed_screen(PushScreen(branches), self.push_branch)

    def push_branch(self, branch: Optional[str]) -> None:
        if branch is None or self.selected_repository is None:
            return
        self.set_diff(f"Preparing push to origin/{branch}...\n\nRunning: git push -u origin {branch}")
        self.call_after_refresh(self.run_push, branch)

    def run_push(self, branch: str) -> None:
        if self.selected_repository is None:
            return
        result = repositories.push(self.selected_repository, branch)
        self.show_status()
        self.set_diff(f"Push to origin/{branch}\n\n{result}")

    def current_change_path(self) -> Optional[str]:
        index = self.query_one("#changes", ListView).index
        if index is None or index < 0 or index >= len(self.changes):
            return None
        return self.changes[index].path

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

    def action_window_prefix(self) -> None:
        self.awaiting_window_command = True

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
        self.import_from(path)
        status.update(f"{len(self.repositories)} repositories registered.")

    def sync_source_file(self) -> None:
        source = repositories.load_source_file()
        candidates = [source] if source else []
        if not source:
            candidates.append(Path.cwd() / "repos.txt")
        for candidate in candidates:
            if candidate.is_file():
                self.import_from(candidate)
                break

    def import_from(self, path: Path) -> None:
        result = repositories.import_file(path, self.repositories)
        self.repositories.extend(result.repositories)
        repositories.save(self.repositories)
        repositories.save_source_file(path)
        self.refresh_repositories()


def main() -> None:
    GitCliApp().run()


if __name__ == "__main__":
    main()
