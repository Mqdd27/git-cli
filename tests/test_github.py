import unittest
from unittest.mock import patch

from git_cli import github


class GitHubStatusTests(unittest.TestCase):
    @patch("git_cli.github.shutil.which", return_value=None)
    def test_reports_missing_gh(self, _which: object) -> None:
        result = github.status()

        self.assertFalse(result.available)
        self.assertFalse(result.authenticated)


if __name__ == "__main__":
    unittest.main()
