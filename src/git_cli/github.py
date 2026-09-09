import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubStatus:
    available: bool
    authenticated: bool
    message: str


def status() -> GitHubStatus:
    if shutil.which("gh") is None:
        return GitHubStatus(False, False, "GitHub CLI (gh) is not installed.")

    result = subprocess.run(
        ["gh", "auth", "status"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return GitHubStatus(True, True, "GitHub is connected.")
    return GitHubStatus(True, False, "GitHub login is required.")


def login() -> bool:
    return subprocess.run(["gh", "auth", "login", "--web"], check=False).returncode == 0
