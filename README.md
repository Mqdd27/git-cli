# Git CLI

A terminal UI for monitoring and managing local Git repositories with GitHub integration.

## Requirements

- Python 3.9 or later
- Git
- [GitHub CLI](https://cli.github.com/) (`gh`) for GitHub login and issue management

## Install

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Run the application:

```sh
git-cli
```

On the first run, select **Log in to GitHub** if `gh` is not already authenticated. The login flow is handled by `gh auth login --web`; credentials remain managed by GitHub CLI and the operating system keychain.

## Import repositories

Create a text file containing one local repository path per line:

```text
# repos.txt
~/code/api
~/code/web
/Users/name/work/project-a
```

Repositories must already be cloned locally and contain a `.git` directory. Relative paths are resolved from the text file location.

In the setup panel, enter the text file path and select **Import repositories**. The registry is saved automatically:

- macOS: `~/Library/Application Support/git-cli/repos.json`
- Linux: `$XDG_CONFIG_HOME/git-cli/repos.json` or `~/.config/git-cli/repos.json`

## Workflow

1. Select a repository from the left panel.
2. Review changed files in the changes panel.
3. Use `v` to select or unselect files, then `s` to stage or unstage them.
4. Use `c` to write a commit message in the centered dialog.
5. Use `p` to select a local branch and push it to `origin`.
6. Use `i` to view GitHub issues for the active repository.

## Key bindings

| Key | Action |
| --- | --- |
| `q` | Quit |
| `g` | Refresh repository status |
| `j` / `k` | Move down / up in the focused panel |
| `Ctrl+W H` | Focus the repository list |
| `Ctrl+W L` | Focus the changes list |
| `Ctrl+W J` | Focus the diff view |
| `Tab` or `d` | Toggle the diff for the active or visually selected changes |
| `v` | Select or unselect the active changed file |
| `s` | Stage unstaged files or unstage staged files |
| `c` | Open the commit message dialog |
| `p` | Select a branch and push to `origin` |
| `i` | Open the GitHub issues dialog |
| `Escape` | Refresh the current repository status |

## Issues

Select an issue with `Enter` to view its body and comments. Use **Reply** to add a comment and **Close issue** to close it after confirmation. GitHub references and mentions work directly in reply text:

```text
Fixes #123
Relates to owner/repository#45
@octocat please review
```
