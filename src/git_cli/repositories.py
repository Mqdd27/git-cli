import json
import os
import platform
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ImportResult:
    repositories: list[Path]
    invalid_paths: list[str]


@dataclass(frozen=True)
class Change:
    code: str
    path: str


@dataclass(frozen=True)
class RepositoryStatus:
    branch: str
    changes: list[Change]


@dataclass(frozen=True)
class CustomTheme:
    name: str
    label: str
    colors: dict[str, str]


THEME_COLORS = {
    "background",
    "surface",
    "surface_alt",
    "text",
    "muted",
    "border",
    "accent",
    "highlight",
    "label",
}


def config_directory() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "git-cli"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "git-cli"


def custom_themes_directory() -> Path:
    return config_directory() / "themes"


def custom_themes() -> list[CustomTheme]:
    directory = custom_themes_directory()
    if not directory.is_dir():
        return []
    themes: list[CustomTheme] = []
    for path in directory.glob("*.json"):
        try:
            value = json.loads(path.read_text())
            colors = value["colors"]
            if not re.fullmatch(r"[a-z0-9-]+", path.stem):
                continue
            if not THEME_COLORS <= colors.keys() or not all(isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in colors.values()):
                continue
            themes.append(CustomTheme(path.stem, value.get("label", path.stem), colors))
        except (OSError, ValueError, json.JSONDecodeError, KeyError):
            continue
    return themes


def registry_path() -> Path:
    return config_directory() / "repos.json"


def preferences_path() -> Path:
    return config_directory() / "preferences.json"


def load_theme() -> str:
    return read_preferences().get("theme", "forest")


def save_theme(theme: str) -> None:
    preferences = read_preferences()
    preferences["theme"] = theme
    write_preferences(preferences)


def load_source_file() -> Path:
    value = read_preferences().get("source_file", "")
    return Path(value) if value else Path()


def save_source_file(path: Path) -> None:
    preferences = read_preferences()
    preferences["source_file"] = str(path)
    write_preferences(preferences)


def read_preferences() -> dict[str, str]:
    try:
        return json.loads(preferences_path().read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write_preferences(preferences: dict[str, str]) -> None:
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(preferences, indent=2) + "\n")


def load() -> list[Path]:
    path = registry_path()
    if not path.exists():
        return []
    try:
        values = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return [Path(value) for value in values if is_repository(Path(value))]


def save(repositories: Iterable[Path]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    values = [str(repository) for repository in repositories]
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(values, indent=2) + "\n")
    temporary_path.replace(path)


def import_file(path: Path, existing: Iterable[Path] = ()) -> ImportResult:
    existing_paths = {repository.resolve() for repository in existing}
    imported: list[Path] = []
    invalid_paths: list[str] = []

    for line in path.read_text().splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        repository = Path(value).expanduser()
        if not repository.is_absolute():
            repository = path.parent / repository
        repository = repository.resolve()
        if not is_repository(repository):
            invalid_paths.append(value)
        elif repository not in existing_paths:
            imported.append(repository)
            existing_paths.add(repository)

    return ImportResult(imported, invalid_paths)


def status(path: Path) -> RepositoryStatus:
    result = run_git(path, "status", "--short", "--branch")
    if result.returncode != 0:
        return RepositoryStatus("Unavailable", [Change("!!", result.stderr.strip() or "Unable to read Git status.")])

    lines = result.stdout.splitlines()
    branch = lines[0].removeprefix("## ") if lines else "Unknown"
    changes = [Change(line[:2], line[3:]) for line in lines[1:]]
    return RepositoryStatus(branch, changes)


def stage(path: Path, changes: Iterable[Change]) -> str:
    selected = list(changes)
    if not selected:
        return "No changes selected."
    staged = [change.path for change in selected if change.code[0] not in (" ", "?")]
    unstaged = [change.path for change in selected if change.code[0] in (" ", "?")]
    results = []
    if staged:
        results.append(run_git(path, "restore", "--staged", "--", *staged))
    if unstaged:
        results.append(run_git(path, "add", "--", *unstaged))
    errors = [result.stderr.strip() for result in results if result.returncode != 0 and result.stderr.strip()]
    return "\n".join(errors) or "Changes updated."


def commit(path: Path, message: str) -> str:
    result = run_git(path, "commit", "-m", message)
    return result.stdout.strip() or result.stderr.strip() or "Commit completed."


def discard(path: Path, changes: Iterable[Change]) -> str:
    tracked = [change.path for change in changes if change.code != "??"]
    if not tracked:
        return "Untracked files are not discarded automatically."
    result = run_git(path, "restore", "--worktree", "--", *tracked)
    return result.stdout.strip() or result.stderr.strip() or "Changes discarded."


def undo_last_commit(path: Path) -> str:
    result = run_git(path, "reset", "--soft", "HEAD~1")
    return result.stdout.strip() or result.stderr.strip() or "Last commit undone; changes remain staged."


def github_repository(path: Path) -> str:
    result = run_git(path, "remote", "get-url", "origin")
    if result.returncode != 0:
        return ""
    url = result.stdout.strip().removesuffix(".git")
    if url.startswith("git@github.com:"):
        return url.removeprefix("git@github.com:")
    if url.startswith("https://github.com/"):
        return url.removeprefix("https://github.com/")
    return ""


def branches(path: Path) -> list[str]:
    result = run_git(path, "branch", "--format=%(refname:short)")
    if result.returncode != 0:
        return []
    return [branch for branch in result.stdout.splitlines() if branch]


def push(path: Path, branch: str) -> str:
    result = run_git(path, "push", "-u", "origin", branch)
    return result.stdout.strip() or result.stderr.strip() or "Push completed."


def pull(path: Path, rebase: bool = False) -> tuple[bool, str]:
    arguments = ("pull", "--rebase") if rebase else ("pull", "--no-rebase")
    result = run_git(path, *arguments)
    output = result.stdout.strip() or result.stderr.strip() or "Pull completed."
    return result.returncode == 0, output


def conflicted_files(path: Path) -> list[str]:
    result = run_git(path, "diff", "--name-only", "--diff-filter=U")
    if result.returncode != 0:
        return []
    return [name for name in result.stdout.splitlines() if name]


def pull_fast_forward(path: Path) -> tuple[bool, str]:
    result = run_git(path, "pull", "--ff-only")
    output = result.stdout.strip() or result.stderr.strip() or "Pull completed."
    return result.returncode == 0, output


def diff(path: Path, change: Change) -> str:
    if change.code == "??":
        return "Untracked files do not have a Git diff. Stage the file first."
    result = run_git(path, "diff", "HEAD", "--", change.path)
    return result.stdout or result.stderr or "No diff available."


def run_git(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *arguments], cwd=path, capture_output=True, text=True, check=False)


def is_repository(path: Path) -> bool:
    return path.is_dir() and (path / ".git").exists()
