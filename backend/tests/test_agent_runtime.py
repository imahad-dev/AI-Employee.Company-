import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.agent_runtime import build_retry_prompt, evaluate_agent_output
from app.core.models import AgentId, AgentOutput, ProjectState


class AgentRuntimeTests(unittest.TestCase):
    def test_quality_rejects_empty_requirements(self):
        state = ProjectState(project_type="dashboard", client_brief="Build a dashboard for testing.")
        output = AgentOutput(phase="architecture", summary="too short", data={})
        quality = evaluate_agent_output(AgentId.requirements_analyst, output, state)
        self.assertLess(quality.score, 8)
        self.assertTrue(quality.retryable)

    def test_quality_accepts_good_requirements(self):
        state = ProjectState(project_type="dashboard", client_brief="Build a dashboard for testing.")
        output = AgentOutput(
            phase="architecture",
            summary="Requirements are ready for architecture handoff.",
            data={"acceptance_criteria": ["Project persists", "Approvals block mutations"]},
        )
        quality = evaluate_agent_output(AgentId.requirements_analyst, output, state)
        self.assertGreaterEqual(quality.score, 8)

    def test_retry_prompt_includes_quality_issues(self):
        state = ProjectState(project_type="dashboard", client_brief="Build a dashboard for testing.")
        output = AgentOutput(phase="wrong", summary="short", data={})
        quality = evaluate_agent_output(AgentId.system_architect, output, state)
        prompt = build_retry_prompt("original", quality)
        self.assertIn("previous output was rejected", prompt)
        self.assertIn("Expected phase", prompt)


if __name__ == "__main__":
    unittest.main()
