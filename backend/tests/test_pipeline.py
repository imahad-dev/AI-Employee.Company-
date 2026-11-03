import asyncio
import unittest
import unittest.mock
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.providers import MockProvider
from app.core.config import Settings
from app.core.models import AgentId, ApprovalRequest, ProjectState
from app.core.pipeline import PipelineService, _running_tasks
from app.db.sqlite import SQLiteStore

TEST_VAULT_KEY = "test-secret-key-with-enough-length"


class PipelineTests(unittest.TestCase):
    def make_service(self):
        local_tmp = Path.cwd() / ".testdata"
        local_tmp.mkdir(exist_ok=True)
        root = local_tmp / uuid4().hex
        root.mkdir(exist_ok=True)
        settings = Settings(
            database_path=root / "platform.db",
            workspace_root=root / "workspace",
            provider_mode="mock",
            max_pipeline_loops=20,
            secret_vault_key=TEST_VAULT_KEY,
        )
        store = SQLiteStore(settings.database_path, settings.secret_vault_key)
        service = PipelineService(store, MockProvider(), settings)
        return root, service, settings

    def test_build_agent_creates_pending_approval_without_file_write(self):
        _root, service, settings = self.make_service()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.")
        service.store.save_project(state)
        approval = asyncio.run(service.build_agent_preview(state.project_id, AgentId.project_manager))
        self.assertEqual(approval.status, "pending")
        self.assertFalse((settings.workspace_root / approval.payload["path"]).exists())

    def test_approval_writes_only_after_approve(self):
        _root, service, settings = self.make_service()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.")
        service.store.save_project(state)
        approval = asyncio.run(service.build_agent_preview(state.project_id, AgentId.project_manager))
        target = settings.workspace_root / approval.payload["path"]
        self.assertFalse(target.exists())
        asyncio.run(service.resolve_approval(approval.approval_id, True))
        self.assertTrue(target.exists())

    def test_mock_pipeline_completes_with_summaries(self):
        _root, service, _settings = self.make_service()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.")
        state.status = "running"
        service.store.save_project(state)
        asyncio.run(service.run(state.project_id))
        finished = service.store.get_project(state.project_id)
        self.assertIsNotNone(finished)
        self.assertEqual(finished.status, "completed")
        self.assertGreaterEqual(len(finished.summaries), 1)
        self.assertGreaterEqual(len(finished.approvals), 1)

    def test_resume_spawns_pipeline_without_restart_side_effects(self):
        _root, service, _settings = self.make_service()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.", status="running")
        service.store.save_project(state)
        resumed = asyncio.run(service.resume(state.project_id))
        self.assertEqual(resumed.status, "running")
        logs = service.store.list_audit_logs(state.project_id)
        self.assertTrue(any(log.action == "pipeline_resumed_after_restart" for log in logs))
        self.assertIn(state.project_id, _running_tasks)
        _running_tasks[state.project_id].cancel()

    def test_atomic_file_write_leaves_target_intact_on_failure(self):
        root, service, settings = self.make_service()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.")
        service.store.save_project(state)
        workspace_root = settings.workspace_root / state.project_id
        workspace_root.mkdir(parents=True, exist_ok=True)
        target = workspace_root / "stable.txt"
        target.write_text("original-content", encoding="utf-8")
        approval = ApprovalRequest(
            project_id=state.project_id,
            agent_id="project_manager",
            kind="file_write",
            title="Write file",
            payload={"path": "stable.txt", "content": "updated-content"},
        )

        original_replace = __import__("os").replace

        def failing_replace(src, dst):
            if str(dst).endswith("stable.txt"):
                raise OSError("simulated crash before rename")
            return original_replace(src, dst)

        with unittest.mock.patch("app.core.pipeline.os.replace", side_effect=failing_replace):
            with self.assertRaises(OSError):
                service._apply_approved_action(approval)

        self.assertEqual(target.read_text(encoding="utf-8"), "original-content")
        self.assertFalse(target.with_suffix(".tmp").exists())

    def test_budget_ceiling_pauses_pipeline_and_queues_governance_review(self):
        _root, service, _settings = self.make_service()
        state = ProjectState(project_type="dashboard", client_brief="Build a useful dashboard for testing.", status="running")
        state.budget.max_total_tokens = 10
        state.token_usage.input_tokens = 10
        service.store.save_project(state)

        asyncio.run(service.run(state.project_id))

        paused = service.store.get_project(state.project_id)
        self.assertEqual(paused.status, "paused")
        actions = service.store.list_action_requests(state.project_id)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].connector_id, "governance")
        self.assertEqual(actions[0].status, "queued")


if __name__ == "__main__":
    unittest.main()
