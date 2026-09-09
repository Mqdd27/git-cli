import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_cli import repositories


class RepositoryImportTests(unittest.TestCase):
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

    @patch("git_cli.repositories.subprocess.run")
    def test_reads_branch_and_clean_working_tree(self, run: object) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = "## main\n"

        result = repositories.status(Path("."))

        self.assertEqual(result.branch, "main")
        self.assertEqual(result.changes, "Working tree clean.")


if __name__ == "__main__":
    unittest.main()
