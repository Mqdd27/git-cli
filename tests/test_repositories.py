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
    def test_reads_diff_for_tracked_file(self, run_git: object) -> None:
        run_git.return_value.stdout = "diff --git a/README.md b/README.md\n"
        change = repositories.Change(" M", "README.md")

        result = repositories.diff(Path("."), change)

        self.assertEqual(result, "diff --git a/README.md b/README.md\n")
        run_git.assert_called_once_with(Path("."), "diff", "HEAD", "--", "README.md")


if __name__ == "__main__":
    unittest.main()
