from __future__ import annotations

from app.agents.catalog import AGENT_CONFIGS, AgentConfig
from app.core.models import AgentId
from app.core.models import ProjectState


def system_prompt(config: AgentConfig) -> str:
    return f"""You are the AI {config.name} in an autonomous software company.
Role: {config.role}

Operating standard:
- Act like a senior specialist shipping production work, not a brainstorming assistant.
- Make every decision traceable to requirements, design, security, deployment, or maintenance impact.
- Include concrete acceptance criteria, contracts, file plans, risks, and handoff notes when relevant.
- Prefer small approval-gated artifacts over vague promises.
- Do not invent completed deployment or command execution; propose approval items instead.

Return strict JSON only with this shape:
{{
  "phase": "{config.next_phase}",
  "summary": "short operational summary",
  "data": {{}},
  "artifacts": [],
  "approvals": [],
  "errors": []
}}

Do not include Markdown outside JSON. Use concrete, implementation-ready details.
Approval objects must be proposed only for file writes, dependency installs, shell commands, commits, or deployment plans.
"""


def build_user_prompt(agent_id: AgentId, state: ProjectState) -> str:
    config = AGENT_CONFIGS[agent_id]
    summaries = "\n".join(f"- {item}" for item in state.summaries[-5:]) or "No summaries yet."
    return f"""Project ID: {state.project_id}
Project type: {state.project_type}
Current phase: {state.current_phase}
Client brief:
{state.client_brief}

Timeline: {state.timeline or "not specified"}
Stack preferences: {state.stack_preferences or "not specified"}

Recent summaries:
{summaries}

Existing phase outputs:
- sprint_plan: {state.sprint_plan}
- requirements: {state.requirements}
- architecture: {state.architecture}
- design_spec: {state.design_spec}
- component_plan: {state.component_plan}
- backend_plan: {state.backend_plan}
- database_plan: {state.database_plan}
- test_results: {state.test_results}
- review_feedback: {state.review_feedback[-2:]}
- security_report: {state.security_report}
- deployment_config: {state.deployment_config}
- docs: {state.docs}
- incidents: {state.incidents[-3:]}
- agent_quality: {state.agent_quality}

Complete the {config.name} work now. Write the main result in "data".
Your output will be quality-scored. Empty data, wrong phase, missing acceptance criteria, weak architecture detail, and vague implementation handoffs will be retried or rejected.
"""
