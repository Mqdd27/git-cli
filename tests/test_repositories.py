import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_cli import repositories


class RepositoryTests(unittest.TestCase):
    def test_imports_valid_repositories_and_skips_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository = root / "repo"
            repository.mkdir()
            (repository / ".git").mkdir()
            source = root / "repos.txt"
            source.write_text("# monitored repositories\nrepo\nmissing\n\n")

            result = repositories.import_file(source)

            self.assertEqual(result.repositories, [repository.resolve()])
            self.assertEqual(result.invalid_paths, ["missing"])

    @patch("git_cli.repositories.run_git")
    def test_reads_branch_and_changes(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stdout = "## main\n M README.md\n?? new.txt\n"

        result = repositories.status(Path("."))

        self.assertEqual(result.branch, "main")
        self.assertEqual(
            result.changes,
            [repositories.Change(" M", "README.md"), repositories.Change("??", "new.txt")],
        )

    @patch("git_cli.repositories.run_git")
    def test_stages_unstaged_changes(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stderr = ""

        result = repositories.stage(Path("."), [repositories.Change(" M", "README.md")])

        self.assertEqual(result, "Changes updated.")
        run_git.assert_called_once_with(Path("."), "add", "--", "README.md")

    @patch("git_cli.repositories.run_git")
    def test_commits_message(self, run_git: object) -> None:
        run_git.return_value.stdout = "[main abc123] Add feature\n"

        result = repositories.commit(Path("."), "Add feature")

        self.assertEqual(result, "[main abc123] Add feature")
        run_git.assert_called_once_with(Path("."), "commit", "-m", "Add feature")

    @patch("git_cli.repositories.run_git")
    def test_undoes_last_commit_and_keeps_changes_staged(self, run_git: object) -> None:
        run_git.return_value.stdout = ""
        run_git.return_value.stderr = ""

        result = repositories.undo_last_commit(Path("."))

        self.assertEqual(result, "Last commit undone; changes remain staged.")
        run_git.assert_called_once_with(Path("."), "reset", "--soft", "HEAD~1")

    @patch("git_cli.repositories.run_git")
    def test_discards_tracked_changes(self, run_git: object) -> None:
        run_git.return_value.stdout = ""
        run_git.return_value.stderr = ""

        result = repositories.discard(Path("."), [repositories.Change(" M", "README.md")])

        self.assertEqual(result, "Changes discarded.")
        run_git.assert_called_once_with(Path("."), "restore", "--worktree", "--", "README.md")

    def test_does_not_discard_untracked_files(self) -> None:
        result = repositories.discard(Path("."), [repositories.Change("??", "new.txt")])

        self.assertEqual(result, "Untracked files are not discarded automatically.")

    @patch("git_cli.repositories.run_git")
    def test_reads_github_origin(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stdout = "git@github.com:owner/repository.git\n"

        result = repositories.github_repository(Path("."))

        self.assertEqual(result, "owner/repository")

    @patch("git_cli.repositories.run_git")
    def test_lists_local_branches(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stdout = "main\nfeature/test\n"

        result = repositories.branches(Path("."))

        self.assertEqual(result, ["main", "feature/test"])
        run_git.assert_called_once_with(Path("."), "branch", "--format=%(refname:short)")

    @patch("git_cli.repositories.run_git")
    def test_pushes_selected_branch(self, run_git: object) -> None:
        run_git.return_value.stdout = "branch 'main' set up to track 'origin/main'.\n"

        result = repositories.push(Path("."), "main")

        self.assertEqual(result, "branch 'main' set up to track 'origin/main'.")
        run_git.assert_called_once_with(Path("."), "push", "-u", "origin", "main")

    @patch("git_cli.repositories.run_git")
    def test_pulls_fast_forward_only(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stdout = "Already up to date.\n"

        completed, result = repositories.pull_fast_forward(Path("."))

        self.assertTrue(completed)
        self.assertEqual(result, "Already up to date.")
        run_git.assert_called_once_with(Path("."), "pull", "--ff-only")

    @patch("git_cli.repositories.run_git")
    def test_pulls_without_rebase_by_default(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stdout = "Merge made by the 'ort' strategy.\n"

        completed, result = repositories.pull(Path("."))

        self.assertTrue(completed)
        self.assertEqual(result, "Merge made by the 'ort' strategy.")
        run_git.assert_called_once_with(Path("."), "pull", "--no-rebase")

    @patch("git_cli.repositories.run_git")
    def test_pulls_with_rebase_when_selected(self, run_git: object) -> None:
        run_git.return_value.returncode = 0
        run_git.return_value.stdout = "Successfully rebased and updated refs/heads/main.\n"

        completed, result = repositories.pull(Path("."), rebase=True)

        self.assertTrue(completed)
        self.assertIn("Successfully rebased", result)
        run_git.assert_called_once_with(Path("."), "pull", "--rebase")

    @patch("git_cli.repositories.run_git")
    def test_reads_diff_for_tracked_file(self, run_git: object) -> None:
        run_git.return_value.stdout = "diff --git a/README.md b/README.md\n"
        change = repositories.Change(" M", "README.md")

        result = repositories.diff(Path("."), change)

        self.assertEqual(result, "diff --git a/README.md b/README.md\n")
        run_git.assert_called_once_with(Path("."), "diff", "HEAD", "--", "README.md")


if __name__ == "__main__":
    unittest.main()
