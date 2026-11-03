import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.models import ConnectorSetting, ProjectState
from app.core.policy import create_action_request


class ConnectorPolicyTests(unittest.TestCase):
    def make_state(self) -> ProjectState:
        return ProjectState(
            project_type="dashboard",
            client_brief="Build a dashboard with safe autonomous operations.",
            connector_settings={
                "web_research": ConnectorSetting(enabled=True, allowed_capabilities=["search", "fetch"]),
                "github_write": ConnectorSetting(enabled=True, allowed_capabilities=["contents.write"]),
            },
        )

    def test_read_action_is_auto_approved_when_connector_is_enabled(self):
        action = create_action_request(
            self.make_state(),
            "web_research",
            "search",
            "https://example.com/search?q=architecture",
            {"query": "safe agent architecture"},
        )
        self.assertEqual(action.status, "approved")
        self.assertEqual(action.risk, "read")

    def test_first_github_write_is_queued_using_normalized_target(self):
        action = create_action_request(
            self.make_state(),
            "github_write",
            "contents.write",
            "https://github.com/Owner/Repo.git/src/app.py",
            {"content": "print('safe')"},
        )
        self.assertEqual(action.status, "queued")
        self.assertEqual(action.risk, "write")
        self.assertEqual(action.normalized_target, "owner/repo/src/app.py")

    def test_disabled_connector_cannot_propose_action(self):
        state = ProjectState(project_type="dashboard", client_brief="Build a dashboard with safe autonomous operations.")
        with self.assertRaises(PermissionError):
            create_action_request(state, "web_research", "search", "example.com", {"query": "test"})

    def test_backlog_blocks_new_action(self):
        state = self.make_state()
        state.budget.max_pending_actions = 0
        action = create_action_request(state, "github_write", "contents.write", "owner/repo/file.py", {"content": "x"})
        self.assertEqual(action.status, "blocked")

    def test_persisted_action_backlog_blocks_without_legacy_approval(self):
        action = create_action_request(
            self.make_state(),
            "github_write",
            "contents.write",
            "owner/repo/file.py",
            {"content": "x"},
            pending_action_count=20,
        )
        self.assertEqual(action.status, "blocked")


if __name__ == "__main__":
    unittest.main()
