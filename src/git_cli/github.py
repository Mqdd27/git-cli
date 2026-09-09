import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GitHubStatus:
    available: bool
    authenticated: bool
    message: str


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    state: str
    body: str
    comments: list[str]


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


def issues(repository: str) -> tuple[list[Issue], str]:
    result = run("issue", "list", "--repo", repository, "--limit", "100", "--json", "number,title,state")
    if result.returncode != 0:
        return [], result.stderr.strip() or "Unable to read GitHub issues."
    return [Issue(issue["number"], issue["title"], issue["state"], "", []) for issue in json.loads(result.stdout)], ""


def issue(repository: str, number: int) -> tuple[Optional[Issue], str]:
    result = run("issue", "view", str(number), "--repo", repository, "--json", "number,title,state,body,comments")
    if result.returncode != 0:
        return None, result.stderr.strip() or "Unable to read GitHub issue."
    value = json.loads(result.stdout)
    comments = [f"{comment['author']['login']}:\n{comment['body']}" for comment in value["comments"]]
    return Issue(value["number"], value["title"], value["state"], value["body"], comments), ""


def comment(repository: str, number: int, body: str) -> str:
    result = run("issue", "comment", str(number), "--repo", repository, "--body", body)
    return result.stdout.strip() or result.stderr.strip() or "Comment added."


def close(repository: str, number: int) -> str:
    result = run("issue", "close", str(number), "--repo", repository)
    return result.stdout.strip() or result.stderr.strip() or "Issue closed."


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *arguments], capture_output=True, text=True, check=False)
