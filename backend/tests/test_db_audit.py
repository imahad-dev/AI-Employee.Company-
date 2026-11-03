import unittest
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import DEFAULT_DEV_VAULT_KEY, PROMPT_LOG_MAX_CHARS
from app.core.models import ActionRequest, AgentExecutionLog, ProjectState
from app.db.sqlite import CHECKPOINT_RETENTION, SQLiteStore

TEST_VAULT_KEY = "test-secret-key-with-enough-length"


class DatabaseAuditTests(unittest.TestCase):
    def make_store(self) -> SQLiteStore:
        root = Path.cwd() / ".testdata" / uuid4().hex
        root.mkdir(parents=True, exist_ok=True)
        return SQLiteStore(root / "audit.db", TEST_VAULT_KEY)

    def test_default_vault_key_is_rejected(self):
        root = Path.cwd() / ".testdata" / uuid4().hex
        root.mkdir(parents=True, exist_ok=True)
        with self.assertRaises(ValueError):
            SQLiteStore(root / "reject.db", DEFAULT_DEV_VAULT_KEY)

    def test_checkpoint_rotation_keeps_last_ten(self):
        store = self.make_store()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.")
        for _ in range(CHECKPOINT_RETENTION + 5):
            store.save_project(state)
        with store.connect() as conn:
            count = conn.execute("select count(*) from checkpoints where project_id = ?", (state.project_id,)).fetchone()[0]
        self.assertEqual(count, CHECKPOINT_RETENTION)

    def test_execution_logs_persist_and_truncate_prompts(self):
        store = self.make_store()
        long_prompt = "x" * (PROMPT_LOG_MAX_CHARS + 500)
        store.save_agent_execution_log(
            AgentExecutionLog(
                project_id="proj_logs",
                agent_id="frontend_developer",
                latency_ms=120,
                input_tokens=10,
                output_tokens=20,
                prompt_system=long_prompt,
                prompt_user=long_prompt,
                json_repair_success=True,
            )
        )
        logs = store.list_agent_execution_logs("proj_logs")
        self.assertEqual(len(logs), 1)
        self.assertEqual(len(logs[0].prompt_system), PROMPT_LOG_MAX_CHARS)
        self.assertEqual(len(logs[0].prompt_user), PROMPT_LOG_MAX_CHARS)
        self.assertTrue(logs[0].json_repair_success)

    def test_retry_cancels_only_actions_from_superseded_attempt(self):
        store = self.make_store()
        stale = ActionRequest(
            project_id="proj_retry",
            connector_id="github_write",
            capability="contents.write",
            normalized_target="owner/repo/file.py",
            payload={"content": "draft"},
            risk="write",
            reason="Requires approval.",
            attempt_id="frontend_developer:1",
        )
        current = stale.model_copy(update={"action_id": str(uuid4()), "attempt_id": "frontend_developer:2"})
        store.add_action_request(stale)
        store.add_action_request(current)

        cancelled = store.cancel_actions_for_attempt("proj_retry", "frontend_developer:1", "Superseded by retry.")

        self.assertEqual([action.action_id for action in cancelled], [stale.action_id])
        self.assertEqual(store.get_action_request(stale.action_id).status, "cancelled")
        self.assertEqual(store.get_action_request(current.action_id).status, "queued")


if __name__ == "__main__":
    unittest.main()
