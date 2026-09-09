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
class RepositoryStatus:
    branch: str
    changes: str


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
    repositories: list[Path] = []
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
            repositories.append(repository)
            existing_paths.add(repository)

    return ImportResult(repositories, invalid_paths)


def status(path: Path) -> RepositoryStatus:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return RepositoryStatus("Unavailable", result.stderr.strip() or "Unable to read Git status.")

    lines = result.stdout.splitlines()
    branch = lines[0].removeprefix("## ") if lines else "Unknown"
    changes = "\n".join(lines[1:]) or "Working tree clean."
    return RepositoryStatus(branch, changes)


def is_repository(path: Path) -> bool:
    return path.is_dir() and (path / ".git").exists()
