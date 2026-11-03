# Autonomous AI Software Company Platform V1

[![CI](https://github.com/imahad-dev/AI-Employee.Company-/actions/workflows/ci.yml/badge.svg)](https://github.com/imahad-dev/AI-Employee.Company-/actions/workflows/ci.yml)

Local-first platform for running a 14-agent AI software company pipeline with streamed progress, SQLite persistence, generated artifacts, and human approval gates.

## Quick Start

Docker:

```powershell
copy .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. The API runs at `http://localhost:8000`.

One-command local helper on Windows:

```powershell
.\scripts\dev.ps1 start
```

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## GitHub Delivery

The dashboard can create a GitHub repository, generate a pull request from approval-gated workspace files, run PR preflight checks, and poll merge-readiness status. Paste a GitHub token in the project GitHub workflow panel; the token is kept in memory for the current backend process and is not written to SQLite.

## Safe Defaults

- `PROVIDER_MODE=mock` by default, so development does not spend API credits.
- Project-level provider selection supports Anthropic, OpenAI, Gemini, Groq, OpenRouter, and local OpenAI-compatible model servers.
- `MAX_PIPELINE_LOOPS=10`.
- Optional `OPERATOR_API_KEY` protects mutating API endpoints when enabled.
- Project provider and GitHub tokens are stored encrypted at rest with `SECRET_VAULT_KEY`.
- Agent outputs are quality-scored and retried before handoff when they miss required detail.
- File writes, dependency installs, commits, shell commands, and deployment actions are stored as approval requests before any mutation.
- The Performance Agent is deferred to V1.1 and represented as a UI placeholder.

## Repository Quality

- GitHub Actions runs backend tests, backend compile checks, and frontend production builds on every push and pull request.
- Docker image builds are checked in CI so the one-command local launch stays healthy.
- Dependabot opens weekly dependency update PRs for Python, npm, and GitHub Actions.
- Pull request and issue templates guide contributors through validation, risk review, and safety checks.
- Release preparation is documented in `docs/release-guide.md`.

## Common Commands

```powershell
.\scripts\dev.ps1 test
.\scripts\dev.ps1 build
.\scripts\dev.ps1 docker-up
.\scripts\dev.ps1 docker-down
```

On Unix-like shells, the same tasks are available through `make test`, `make build`, and `make docker-up`.
