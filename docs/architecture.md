# Architecture

The platform is split into a FastAPI backend and a Next.js frontend.

## Backend

- `ProjectState` is the shared state passed through the pipeline.
- `PipelineService` runs the approval-gated orchestration loop.
- `route_next` owns phase transitions and retry loops.
- `summarize_state` compresses state after every 3 completed agents.
- `SQLiteStore` persists projects, checkpoints, events, summaries, artifacts, approvals, and runs.
- `MockProvider` is the default LLM provider for no-cost development.
- `AnthropicProvider` uses the Messages API when `PROVIDER_MODE=anthropic`.

LangGraph is declared as a dependency and `app.core.graph.build_langgraph_app` builds a graph object when the package is installed. The runtime service uses the same routing rules with a fallback runner so local mock development works even before optional orchestration dependencies are installed.

## Safety

Agents do not directly mutate the workspace. They propose artifacts or approval requests. Approval resolution applies only allowed actions, and file writes are constrained to the configured workspace root.

## Deferred

The Performance Agent is represented in the dashboard but deferred to V1.1.

