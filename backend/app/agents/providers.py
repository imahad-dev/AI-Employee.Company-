from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx
from json_repair import repair_json

from app.agents.catalog import AGENT_CONFIGS
from app.core.config import Settings
from app.core.credentials import get_project_credentials
from app.core.http import get_http_client
from app.core.models import AgentId, AgentOutput, ProjectState, TokenUsage

_provider_semaphore = asyncio.Semaphore(5)


@dataclass(frozen=True)
class ProviderProfile:
    id: str
    name: str
    kind: str
    default_model: str
    env_keys: tuple[str, ...]
    notes: str


PROVIDER_PROFILES: tuple[ProviderProfile, ...] = (
    ProviderProfile("mock", "Mock Provider", "offline", "mock-fast", (), "No-cost deterministic provider for tests and demos."),
    ProviderProfile("anthropic", "Anthropic Claude", "native", "claude-sonnet-4-20250514", ("ANTHROPIC_API_KEY",), "Direct Anthropic Messages API."),
    ProviderProfile("openai", "OpenAI", "openai-compatible", "gpt-4.1-mini", ("OPENAI_API_KEY",), "OpenAI chat completions API."),
    ProviderProfile("gemini", "Google Gemini", "native", "gemini-2.5-flash", ("GEMINI_API_KEY",), "Direct Gemini generateContent API."),
    ProviderProfile("groq", "Groq", "openai-compatible", "llama-3.3-70b-versatile", ("GROQ_API_KEY",), "Low-latency OpenAI-compatible endpoint."),
    ProviderProfile("openrouter", "OpenRouter", "openai-compatible", "anthropic/claude-3.5-sonnet", ("OPENROUTER_API_KEY",), "Routes many hosted commercial and open models."),
    ProviderProfile("local", "Local OpenAI-Compatible", "openai-compatible", "llama3.1", ("LOCAL_BASE_URL",), "Works with Ollama, vLLM, LM Studio, LocalAI, and similar servers."),
)


class LlmProvider(ABC):
    @abstractmethod
    async def complete_agent(self, agent_id: AgentId, system: str, user: str, state: ProjectState) -> AgentOutput:
        raise NotImplementedError


class MockProvider(LlmProvider):
    async def complete_agent(self, agent_id: AgentId, system: str, user: str, state: ProjectState) -> AgentOutput:
        config = AGENT_CONFIGS[agent_id]
        data = self._data_for(agent_id, state)
        approvals = []
        artifacts = []
        if agent_id in {AgentId.frontend_developer, AgentId.backend_developer, AgentId.devops_agent}:
            approvals.append(
                {
                    "kind": "file_write" if agent_id != AgentId.devops_agent else "deployment_plan",
                    "title": f"Approve {config.name} generated artifact",
                    "payload": {"path": f"{state.project_id}/{agent_id.value}.json", "content": data},
                }
            )
        if agent_id in {AgentId.frontend_developer, AgentId.backend_developer, AgentId.docs_writer}:
            artifacts.append({"name": f"{config.name} output", "kind": "json", "content": data})
        return AgentOutput(
            phase=config.next_phase,
            summary=f"{config.name} completed mock work for {state.project_type}.",
            data=data,
            artifacts=artifacts,
            approvals=approvals,
            token_usage=TokenUsage(input_tokens=900, output_tokens=500, estimated_cost_usd=0.02),
        )

    def _data_for(self, agent_id: AgentId, state: ProjectState) -> dict[str, Any]:
        if agent_id == AgentId.project_manager:
            return {"milestones": ["intake", "design", "development", "quality", "deployment plan", "maintenance"], "assignments": [agent.value for agent in AGENT_CONFIGS], "priority": "approval-gated local-first delivery"}
        if agent_id == AgentId.requirements_analyst:
            return {"user_stories": ["As an operator, I can create a project and watch the pipeline run."], "acceptance_criteria": ["Project state persists", "Approvals block mutations", "Events stream live"], "edge_cases": ["LLM JSON invalid", "Loop budget exceeded", "Rejected approval"]}
        if agent_id == AgentId.system_architect:
            return {"stack": ["FastAPI", "LangGraph", "SQLite", "Next.js", "Tailwind"], "api": ["POST /api/projects", "POST /api/projects/{id}/start", "GET /api/projects/{id}/events"], "storage": "SQLite with replaceable repository interface"}
        if agent_id == AgentId.ui_designer:
            return {"screens": ["project intake", "pipeline board", "agent detail", "approval inbox"], "style": "dense operational dashboard"}
        if agent_id == AgentId.component_planner:
            return {"components": ["ProjectForm", "PipelineBoard", "AgentDetail", "ApprovalInbox", "EventStream"]}
        if agent_id == AgentId.frontend_developer:
            return {"files": {"frontend/app/page.tsx": "dashboard implementation preview"}, "states": ["loading", "error", "streaming"]}
        if agent_id == AgentId.backend_developer:
            return {"services": ["project service", "pipeline service", "approval service"], "auth": "local dev mode"}
        if agent_id == AgentId.database_agent:
            return {"tables": ["projects", "agent_runs", "artifacts", "approvals", "events", "summaries"], "indexes": ["project_id"]}
        if agent_id == AgentId.qa_agent:
            return {"failed": [], "coverage": "routing and approval unit tests", "status": "passed"}
        if agent_id == AgentId.code_reviewer:
            return {"score": 8, "comments": ["Mock implementation is coherent for V1."], "approved": True}
        if agent_id == AgentId.security_agent:
            return {"critical": [], "recommendations": ["Keep approval gates mandatory", "Do not log secrets"]}
        if agent_id == AgentId.devops_agent:
            return {"deployment_plan": "Generate Docker/Vercel/GitHub Actions configs only; no cloud deploy in V1."}
        if agent_id == AgentId.docs_writer:
            return {"readme": "Generated project documentation", "operator_guide": "Use mock mode until API budgets are set."}
        if agent_id == AgentId.monitor_agent:
            return {"incidents": [], "feedback_summary": "No live incidents in local V1."}
        return {"result": "ok"}


class AnthropicProvider(LlmProvider):
    def __init__(self, settings: Settings, api_key: str | None = None) -> None:
        self.settings = settings
        import anthropic

        self.client = anthropic.AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    async def complete_agent(self, agent_id: AgentId, system: str, user: str, state: ProjectState) -> AgentOutput:
        response = await self.client.messages.create(
            model=resolve_model(state, agent_id, self.settings.anthropic_model),
            max_tokens=self.settings.anthropic_max_tokens,
            temperature=self.settings.anthropic_temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        output, _ = parse_agent_output_with_meta(text)
        usage = getattr(response, "usage", None)
        if usage:
            output.token_usage = TokenUsage(
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
                estimated_cost_usd=estimate_cost(getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0)),
            )
        return output


class OpenAICompatibleProvider(LlmProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        base_url: str,
        api_key: str | None,
        default_model: str,
        provider_name: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.settings = settings
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.provider_name = provider_name
        self.extra_headers = extra_headers or {}

    async def complete_agent(self, agent_id: AgentId, system: str, user: str, state: ProjectState) -> AgentOutput:
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": resolve_model(state, agent_id, self.default_model),
            "temperature": self.settings.anthropic_temperature,
            "max_tokens": self.settings.anthropic_max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with _provider_semaphore:
            response = await get_http_client().post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        output, _ = parse_agent_output_with_meta(text)
        usage = data.get("usage") or {}
        output.token_usage = TokenUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            estimated_cost_usd=estimate_cost(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)),
        )
        return output


class GeminiProvider(LlmProvider):
    def __init__(self, settings: Settings, api_key: str | None = None, base_url: str | None = None) -> None:
        self.settings = settings
        self.api_key = api_key or settings.gemini_api_key
        self.base_url = (base_url or settings.gemini_base_url).rstrip("/")

    async def complete_agent(self, agent_id: AgentId, system: str, user: str, state: ProjectState) -> AgentOutput:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for provider_mode=gemini")
        model = resolve_model(state, agent_id, self.settings.gemini_model)
        url = f"{self.base_url}/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": self.settings.anthropic_temperature,
                "maxOutputTokens": self.settings.anthropic_max_tokens,
                "responseMimeType": "application/json",
            },
        }
        async with _provider_semaphore:
            response = await get_http_client().post(url, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
        data = response.json()
        text = "".join(part.get("text", "") for part in data["candidates"][0]["content"].get("parts", []))
        output, _ = parse_agent_output_with_meta(text)
        usage = data.get("usageMetadata") or {}
        output.token_usage = TokenUsage(
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            estimated_cost_usd=estimate_cost(usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)),
        )
        return output


class ProviderRouter(LlmProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete_agent(self, agent_id: AgentId, system: str, user: str, state: ProjectState) -> AgentOutput:
        mode = (state.provider_mode or self.settings.provider_mode).lower()
        return await build_provider_for_project(self.settings, mode, state).complete_agent(agent_id, system, user, state)


def resolve_model(state: ProjectState, agent_id: AgentId, default_model: str) -> str:
    return state.agent_model_overrides.get(agent_id.value) or state.model_name or default_model


def extract_json_substring(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start : end + 1]


def parse_agent_output(text: str) -> AgentOutput:
    output, _ = parse_agent_output_with_meta(text)
    return output


def parse_agent_output_with_meta(text: str) -> tuple[AgentOutput, bool]:
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1).strip()
    candidate = extract_json_substring(stripped)
    json_repaired = False
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        repaired = repair_json(candidate)
        payload = json.loads(repaired)
        json_repaired = True
    output = AgentOutput.model_validate(payload)
    if json_repaired:
        output = output.model_copy(update={"json_repaired": True})
    return output, json_repaired


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return round((input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0), 4)


def build_provider_for_mode(settings: Settings, mode: str) -> LlmProvider:
    return build_provider_for_project(settings, mode, None)


def build_provider_for_project(settings: Settings, mode: str, state: ProjectState | None) -> LlmProvider:
    credentials = get_project_credentials(state.project_id) if state else None
    api_key = credentials.api_key if credentials else None
    base_url = credentials.base_url if credentials else None
    if mode == "mock":
        return MockProvider()
    if mode == "anthropic":
        return AnthropicProvider(settings, api_key=api_key)
    if mode == "gemini":
        return GeminiProvider(settings, api_key=api_key, base_url=base_url)
    if mode == "openai":
        return OpenAICompatibleProvider(settings, base_url=base_url or settings.openai_base_url, api_key=api_key or settings.openai_api_key, default_model=settings.openai_model, provider_name="openai")
    if mode == "groq":
        return OpenAICompatibleProvider(settings, base_url=base_url or settings.groq_base_url, api_key=api_key or settings.groq_api_key, default_model=settings.groq_model, provider_name="groq")
    if mode == "openrouter":
        headers = {"HTTP-Referer": settings.openrouter_site_url or "", "X-Title": settings.openrouter_app_name}
        headers = {key: value for key, value in headers.items() if value}
        return OpenAICompatibleProvider(settings, base_url=base_url or settings.openrouter_base_url, api_key=api_key or settings.openrouter_api_key, default_model=settings.openrouter_model, provider_name="openrouter", extra_headers=headers)
    if mode == "local":
        return OpenAICompatibleProvider(settings, base_url=base_url or settings.local_base_url, api_key=api_key or settings.local_api_key, default_model=settings.local_model, provider_name="local")
    raise ValueError(f"Unsupported provider mode: {mode}")


def build_provider(settings: Settings) -> LlmProvider:
    return ProviderRouter(settings)


def provider_profiles() -> list[dict[str, object]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "kind": item.kind,
            "default_model": item.default_model,
            "env_keys": list(item.env_keys),
            "notes": item.notes,
        }
        for item in PROVIDER_PROFILES
    ]
