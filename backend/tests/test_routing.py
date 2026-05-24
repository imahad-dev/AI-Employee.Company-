import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.models import ProjectState
from app.core.routing import route_next, should_summarize


class RoutingTests(unittest.TestCase):
    def make_state(self, phase: str = "intake") -> ProjectState:
        return ProjectState(project_type="dashboard", client_brief="Build a serious test dashboard.", current_phase=phase)

    def test_initial_route_goes_to_project_manager(self):
        state = self.make_state("intake")
        self.assertEqual(route_next(state).value, "project_manager")

    def test_loop_guard_stops_run(self):
        state = self.make_state("intake")
        state.loop_count = 10
        self.assertIsNone(route_next(state, max_loops=10))

    def test_failed_frontend_tests_route_to_frontend(self):
        state = self.make_state("testing")
        state.test_results = {"failed": ["frontend component failed"]}
        self.assertEqual(route_next(state).value, "frontend_developer")

    def test_failed_backend_tests_route_to_backend(self):
        state = self.make_state("testing")
        state.test_results = {"failed": ["api contract failed"]}
        self.assertEqual(route_next(state).value, "backend_developer")

    def test_security_critical_routes_to_backend(self):
        state = self.make_state("security")
        state.security_report = {"critical": ["missing auth"]}
        self.assertEqual(route_next(state).value, "backend_developer")

    def test_review_score_routes_to_frontend(self):
        state = self.make_state("review")
        state.review_feedback = [{"score": 6}]
        self.assertEqual(route_next(state).value, "frontend_developer")

    def test_summarizer_interval(self):
        state = self.make_state("design")
        state.completed_agents = ["a", "b", "c"]
        self.assertTrue(should_summarize(state, 3))


if __name__ == "__main__":
    unittest.main()
