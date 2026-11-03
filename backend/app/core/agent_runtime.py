from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.agents.catalog import AGENT_CONFIGS
from app.core.models import AgentId, AgentOutput, ProjectState


@dataclass
class AgentQuality:
    score: int
    issues: list[str]
    retryable: bool


def evaluate_agent_output(agent_id: AgentId, output: AgentOutput, state: ProjectState) -> AgentQuality:
    issues: list[str] = []
    config = AGENT_CONFIGS[agent_id]
    if output.phase != config.next_phase:
        issues.append(f"Expected phase '{config.next_phase}' but got '{output.phase}'.")
    if len(output.summary.strip()) < 12:
        issues.append("Summary is too short to be operationally useful.")
    if not output.data and agent_id not in {AgentId.monitor_agent}:
        issues.append("Agent returned empty data.")
    if output.errors:
        issues.append("Agent returned errors in its output.")
    if agent_id == AgentId.requirements_analyst:
        criteria = output.data.get("acceptance_criteria", [])
        if not isinstance(criteria, list) or len(criteria) < 2:
            issues.append("Requirements need at least two acceptance criteria.")
    if agent_id == AgentId.system_architect:
        if not any(key in output.data for key in ("stack", "api", "api_spec", "db_schema")):
            issues.append("Architecture output must include stack/API/schema detail.")
    if agent_id in {AgentId.frontend_developer, AgentId.backend_developer}:
        has_delivery = bool(output.data.get("files") or output.artifacts or output.approvals)
        if not has_delivery:
            issues.append("Implementation agent needs files, artifacts, or approvals.")
    score = max(0, 10 - (len(issues) * 2))
    return AgentQuality(score=score, issues=issues, retryable=bool(issues) and score < 8)


def build_retry_prompt(original_prompt: str, quality: AgentQuality) -> str:
    issue_list = "\n".join(f"- {issue}" for issue in quality.issues)
    return f"""{original_prompt}

The previous output was rejected by runtime quality gates:
{issue_list}

Return corrected strict JSON only. Preserve the required schema, fill missing operational detail, and do not explain outside JSON.
"""


class AgentTimer:
    def __enter__(self) -> "AgentTimer":
        self.started = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.duration_ms = int((perf_counter() - self.started) * 1000)
