import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.providers import parse_agent_output, provider_profiles, resolve_model
from app.core.models import AgentId, ProjectState


class ProviderTests(unittest.TestCase):
    def test_provider_profiles_include_requested_backends(self):
        ids = {item["id"] for item in provider_profiles()}
        self.assertTrue({"mock", "anthropic", "openai", "gemini", "groq", "openrouter", "local"}.issubset(ids))

    def test_parse_agent_output_accepts_fenced_json(self):
        output = parse_agent_output(
            """```json
            {"phase":"requirements","summary":"ok","data":{"x":1},"artifacts":[],"approvals":[],"errors":[]}
            ```"""
        )
        self.assertEqual(output.phase, "requirements")
        self.assertEqual(output.data["x"], 1)

    def test_resolve_model_uses_agent_override_then_project_default(self):
        state = ProjectState(
            project_type="dashboard",
            client_brief="Build a useful dashboard for testing.",
            model_name="project-model",
            agent_model_overrides={"frontend_developer": "frontend-model"},
        )
        self.assertEqual(resolve_model(state, AgentId.frontend_developer, "default"), "frontend-model")
        self.assertEqual(resolve_model(state, AgentId.backend_developer, "default"), "project-model")


if __name__ == "__main__":
    unittest.main()

