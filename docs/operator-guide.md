# Operator Guide

## Run In Mock Mode

Mock mode is the default:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

Start the frontend:

```powershell
cd frontend
npm run dev
```

Create a project in the dashboard, start the pipeline, and watch events stream into the activity log.

## Use Anthropic

Set environment variables before launching the backend:

```powershell
$env:PROVIDER_MODE="anthropic"
$env:ANTHROPIC_API_KEY="..."
$env:ANTHROPIC_MODEL="claude-sonnet-4-20250514"
```

Keep `MAX_PIPELINE_LOOPS` low while tuning prompts.

## Use Other Model Providers

The dashboard can select a provider per project. Mock mode remains the default.

Supported provider modes:

- `anthropic`: direct Anthropic Messages API.
- `openai`: OpenAI chat completions.
- `gemini`: direct Gemini `generateContent`.
- `groq`: Groq OpenAI-compatible endpoint.
- `openrouter`: OpenRouter OpenAI-compatible endpoint for many commercial and open models.
- `local`: OpenAI-compatible local servers such as Ollama, vLLM, LM Studio, LocalAI, or text-generation-webui.

Examples:

```powershell
$env:PROVIDER_MODE="groq"
$env:GROQ_API_KEY="..."
$env:GROQ_MODEL="llama-3.3-70b-versatile"
```

```powershell
$env:PROVIDER_MODE="local"
$env:LOCAL_BASE_URL="http://localhost:11434/v1"
$env:LOCAL_MODEL="llama3.1"
```

For OpenRouter:

```powershell
$env:PROVIDER_MODE="openrouter"
$env:OPENROUTER_API_KEY="..."
$env:OPENROUTER_MODEL="meta-llama/llama-3.1-70b-instruct"
```

## Manual UI Checklist

- Create a project.
- Start a mocked pipeline run.
- Watch SSE events update the board.
- Expand agent cards.
- Trigger “Build this agent.”
- Approve and reject generated artifacts.
- Confirm rejected actions do not modify files.
