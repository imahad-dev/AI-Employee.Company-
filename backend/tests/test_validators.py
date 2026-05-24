import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.agents.validators import semantic_errors
from app.core.models import AgentId, AgentOutput, ApprovalRequest


class ValidatorTests(unittest.TestCase):
    def test_requirements_need_acceptance_criteria(self):
        output = AgentOutput(phase="architecture", summary="ok", data={"user_stories": []})
        self.assertIn("requirements must include acceptance_criteria", semantic_errors(AgentId.requirements_analyst, output))

    def test_devops_must_request_approval(self):
        output = AgentOutput(phase="docs", summary="ok", data={"deployment_plan": "ship it"})
        self.assertIn("DevOps output must create an approval-gated deployment plan", semantic_errors(AgentId.devops_agent, output))

    def test_approval_payload_required(self):
        with self.assertRaises(ValidationError):
            ApprovalRequest(project_id="p1", agent_id="a1", kind="file_write", title="empty", payload={})


if __name__ == "__main__":
    unittest.main()
