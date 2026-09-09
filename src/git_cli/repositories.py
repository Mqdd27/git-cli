import json
import os
import platform
import subprocess
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


def registry_path() -> Path:
    if platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "git-cli" / "repos.json"


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


def branches(path: Path) -> list[str]:
    result = run_git(path, "branch", "--format=%(refname:short)")
    if result.returncode != 0:
        return []
    return [branch for branch in result.stdout.splitlines() if branch]


def push(path: Path, branch: str) -> str:
    result = run_git(path, "push", "-u", "origin", branch)
    return result.stdout.strip() or result.stderr.strip() or "Push completed."


def diff(path: Path, change: Change) -> str:
    if change.code == "??":
        return "Untracked files do not have a Git diff. Stage the file first."
    result = run_git(path, "diff", "HEAD", "--", change.path)
    return result.stdout or result.stderr or "No diff available."


def run_git(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )


def is_repository(path: Path) -> bool:
    return path.is_dir() and (path / ".git").exists()
