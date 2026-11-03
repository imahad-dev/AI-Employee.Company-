import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.providers import parse_agent_output, parse_agent_output_with_meta


class ParserTests(unittest.TestCase):
    def test_parse_agent_output_repairs_trailing_commas(self):
        output, repaired = parse_agent_output_with_meta(
            '{"phase":"requirements","summary":"ok","data":{"x":1,},"artifacts":[],"approvals":[],"errors":[],}'
        )
        self.assertTrue(repaired)
        self.assertEqual(output.phase, "requirements")
        self.assertEqual(output.data["x"], 1)

    def test_parse_agent_output_extracts_json_from_prose(self):
        output = parse_agent_output(
            'Here is the plan:\n{"phase":"architecture","summary":"ready","data":{},"artifacts":[],"approvals":[],"errors":[]}\nThanks.'
        )
        self.assertEqual(output.phase, "architecture")

    def test_parse_agent_output_accepts_valid_json_without_repair(self):
        output, repaired = parse_agent_output_with_meta(
            '{"phase":"design","summary":"ok","data":{},"artifacts":[],"approvals":[],"errors":[]}'
        )
        self.assertFalse(repaired)
        self.assertEqual(output.phase, "design")


if __name__ == "__main__":
    unittest.main()
