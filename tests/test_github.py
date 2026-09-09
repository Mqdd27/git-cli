import unittest
from unittest.mock import patch

from git_cli import github


class GitHubStatusTests(unittest.TestCase):
    @patch("git_cli.github.shutil.which", return_value=None)
    def test_reports_missing_gh(self, _which: object) -> None:
        result = github.status()

        self.assertFalse(result.available)
        self.assertFalse(result.authenticated)

    @patch("git_cli.github.run")
    def test_lists_issues(self, run: object) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = '[{"number": 7, "state": "OPEN", "title": "Fix bug"}]'

        issues, message = github.issues("owner/repository")

        self.assertEqual(issues, [github.Issue(7, "Fix bug", "OPEN", "", [])])
        self.assertEqual(message, "")

    @patch("git_cli.github.run")
    def test_reads_issue_detail_and_comments(self, run: object) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = (
            '{"number": 7, "state": "OPEN", "title": "Fix bug", "body": "Details", '
            '"comments": [{"author": {"login": "octocat"}, "body": "@user Please review"}]}'
        )

        issue, message = github.issue("owner/repository", 7)

        self.assertEqual(issue, github.Issue(7, "Fix bug", "OPEN", "Details", ["octocat:\n@user Please review"]))
        self.assertEqual(message, "")

    @patch("git_cli.github.run")
    def test_adds_issue_comment(self, run: object) -> None:
        run.return_value.stdout = "https://github.com/owner/repository/issues/7#issuecomment-1\n"

        result = github.comment("owner/repository", 7, "@octocat Thanks")

        self.assertIn("issuecomment", result)
        run.assert_called_once_with("issue", "comment", "7", "--repo", "owner/repository", "--body", "@octocat Thanks")


if __name__ == "__main__":
    unittest.main()
