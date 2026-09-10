# Git CLI

A terminal UI for monitoring and managing local Git repositories with GitHub integration.

## Requirements

- Python 3.9 or later
- Git
- [GitHub CLI](https://cli.github.com/) (`gh`) for GitHub login and issue management

## Install

### Standalone binary (recommended)

Download the binary matching your platform and architecture, make it executable, then run it:

```sh
chmod +x git-cli
git-cli
```

The current local build is available at `dist/git-cli` and targets macOS Apple Silicon (`arm64`). The binary includes Python and application dependencies; still need system `git` and `gh` for GitHub features.

### From source

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
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

The text file path is remembered. On startup and refresh (`g`), the file is read again, so repositories added later appear without a manual re-import.

## Workflow

1. Select a repository from the left panel.
2. Review changed files in the changes panel.
3. Use `v` to select or unselect files; `Tab` or `d` toggles their diffs.
4. Use `s` to stage or unstage selected files.
5. Use `c` to write a commit message in the centered dialog.
6. Use `p` to select a local branch and push it to `origin`, or `P` to pull.
7. Use `i` to view GitHub issues for the active repository.

## Key bindings

| Key | Action |
| --- | --- |
| `q` | Quit |
| `g` | Refresh repository status |
| `j` / `k` | Move down / up in the focused panel |
| `gg` / `G` | Scroll diff view to top / bottom |
| `Ctrl+D` / `Ctrl+U` | Scroll diff view down / up by half page |
| `Ctrl+W H` | Focus the repository list |
| `Ctrl+W L` / `Ctrl+W K` | Focus the changes list |
| `Ctrl+W J` | Focus the diff view |
| `Tab` or `d` | Toggle the diff for the active or visually selected changes |
| `v` | Select or unselect the active changed file |
| `s` | Stage unstaged files or unstage staged files |
| `d d` | Discard changes in selected files (with confirmation) |
| `c` | Open the commit message dialog |
| `u` | Undo the last commit (`git reset --soft HEAD~1`) |
| `p` | Select a branch and push to `origin` |
| `P` | Pull the active branch; choose rebase or merge strategy |
| `T` | Change the color theme |
| `i` | Open the GitHub issues dialog |
| `Escape` | Refresh the current repository status |

## Custom themes

Create a JSON file in the custom theme directory:

- macOS: `~/Library/Application Support/git-cli/themes/`
- Linux: `$XDG_CONFIG_HOME/git-cli/themes/` or `~/.config/git-cli/themes/`

Example `solarized.json`:

```json
{
  "label": "Solarized Dark",
  "colors": {
    "background": "#002b36",
    "surface": "#073642",
    "surface_alt": "#00212b",
    "text": "#839496",
    "muted": "#586e75",
    "border": "#586e75",
    "accent": "#2aa198",
    "highlight": "#b58900",
    "label": "#cb4b16"
  }
}
```

Restart Git CLI, then use `T` and select the custom theme. The JSON filename becomes the theme ID; `label` is the name shown in the selector.

## Pull conflicts

When a pull cannot fast-forward, a dialog asks whether to merge or rebase. If the pull stops on conflicts, Git CLI detects the conflicted files and opens them in your editor so you can resolve them. After editing, stage the files with `s` and finish the merge or rebase from the terminal.

## Editor configuration

Git CLI opens the editor configured in `$EDITOR` (fallback: `vi`). For GUI editors, make sure to tell the shell to wait for the editor window to close:

```sh
# ~/.zshrc or ~/.bashrc
export EDITOR="code --wait"
export VISUAL="$EDITOR"
```

## Issues

Select an issue with `Enter` to view its body and comments. Use **Reply** to add a comment and **Close issue** to close it after confirmation. GitHub references and mentions work directly in reply text:

```text
Fixes #123
Relates to owner/repository#45
@octocat please review
```
