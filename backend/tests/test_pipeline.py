import asyncio
import unittest
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.providers import MockProvider
from app.core.config import Settings
from app.core.models import AgentId, ProjectState
from app.core.pipeline import PipelineService
from app.db.sqlite import SQLiteStore


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
        )
        store = SQLiteStore(settings.database_path)
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


if __name__ == "__main__":
    unittest.main()
