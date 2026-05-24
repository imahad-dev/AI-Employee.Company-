import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.github import GitHubWorkflowError, build_preflight_report, parse_github_repo, safe_branch_name
from app.core.models import ProjectState, RepositorySettings


class GitHubWorkflowTests(unittest.TestCase):
    def test_parse_repo_formats(self):
        cases = {
            "owner/repo": ("owner", "repo"),
            "owner/repo.git": ("owner", "repo"),
            "https://github.com/owner/repo": ("owner", "repo"),
            "https://github.com/owner/repo.git": ("owner", "repo"),
            "git@github.com:owner/repo.git": ("owner", "repo"),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_github_repo(value), expected)

    def test_parse_repo_rejects_invalid_values(self):
        with self.assertRaises(GitHubWorkflowError):
            parse_github_repo("https://example.com/owner/repo")

    def test_safe_branch_name_defaults_and_sanitizes(self):
        self.assertEqual(safe_branch_name("proj_123"), "ai-company/proj_123")
        self.assertEqual(safe_branch_name("proj_123", "feature/New PR!"), "feature/New-PR")

    def test_preflight_reports_missing_readiness(self):
        root = Path.cwd() / ".testdata" / "github-preflight"
        root.mkdir(parents=True, exist_ok=True)
        state = ProjectState(
            project_id="proj_preflight",
            project_type="dashboard",
            client_brief="Build a dashboard with approval gated delivery.",
            repository=RepositorySettings(provider="local"),
        )
        report = build_preflight_report(state, root, has_token=False)
        self.assertFalse(report["ready"])
        self.assertIn("GitHub provider selected", [check["name"] for check in report["checks"]])


if __name__ == "__main__":
    unittest.main()
