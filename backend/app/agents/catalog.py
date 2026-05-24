from __future__ import annotations

from dataclasses import dataclass

from app.core.models import AgentId


@dataclass(frozen=True)
class AgentConfig:
    id: AgentId
    number: int
    name: str
    phase: str
    short: str
    role: str
    tools: tuple[str, ...]
    outputs: tuple[str, ...]
    sends: str
    state_key: str
    next_phase: str


AGENT_CONFIGS: dict[AgentId, AgentConfig] = {
    AgentId.project_manager: AgentConfig(
        AgentId.project_manager, 1, "Project Manager", "Phase 1 - Intake & planning",
        "Intake, briefs, sprints",
        "Receives the client brief, breaks it into milestones, creates a task graph, assigns priorities, and coordinates the lifecycle.",
        ("Claude API", "Task graph store", "Slack/notify", "SQLite queue"),
        ("Sprint plan", "Agent task assignments", "Timeline & milestones", "Stakeholder summary"),
        "Requirements Analyst, System Architect", "sprint_plan", "requirements",
    ),
    AgentId.requirements_analyst: AgentConfig(
        AgentId.requirements_analyst, 2, "Requirements Analyst", "Phase 1 - Intake & planning",
        "User stories, acceptance",
        "Turns vague project descriptions into structured requirements, user stories, acceptance criteria, edge cases, and features.",
        ("Claude API", "Docs store", "Vector memory"),
        ("User story document", "Acceptance criteria", "Feature breakdown", "Edge case list"),
        "System Architect, UI/UX Designer", "requirements", "architecture",
    ),
    AgentId.system_architect: AgentConfig(
        AgentId.system_architect, 3, "System Architect", "Phase 1 - Intake & planning",
        "Stack, schemas, APIs",
        "Selects the tech stack, defines API contracts, database structure, service boundaries, and scalability strategy.",
        ("Claude API", "Diagram generator", "Docs store"),
        ("Architecture diagram", "Tech stack decision", "API schema (OpenAPI)", "DB schema draft"),
        "Frontend Dev, Backend Dev, Database Agent", "architecture", "design",
    ),
    AgentId.ui_designer: AgentConfig(
        AgentId.ui_designer, 4, "UI/UX Designer", "Phase 2 - Design",
        "Wireframes, design system",
        "Creates wireframes, design tokens, typography specs, and responsive layout plans for every screen.",
        ("Claude API", "Figma MCP", "Design token store"),
        ("Wireframes", "Design system tokens", "Component specs", "Responsive breakpoints"),
        "Component Planner, Frontend Dev", "design_spec", "components",
    ),
    AgentId.component_planner: AgentConfig(
        AgentId.component_planner, 5, "Component Planner", "Phase 2 - Design",
        "Component tree, props",
        "Converts design specs into a component tree with props, state, events, and reuse boundaries.",
        ("Claude API", "Storybook MCP", "Docs store"),
        ("Component tree", "Props interface", "State map", "Storybook stories"),
        "Frontend Dev", "component_plan", "frontend",
    ),
    AgentId.frontend_developer: AgentConfig(
        AgentId.frontend_developer, 6, "Frontend Developer", "Phase 3 - Development",
        "React, Vue, Next.js",
        "Writes frontend code, routing, state management, API integration, and responsive layouts matching the design spec.",
        ("Claude API", "Code executor", "GitHub MCP", "npm runner"),
        ("React/Vue components", "Pages & routing", "State management", "CSS/Tailwind styles"),
        "Code Reviewer, QA & Testing", "code_files", "backend",
    ),
    AgentId.backend_developer: AgentConfig(
        AgentId.backend_developer, 7, "Backend Developer", "Phase 3 - Development",
        "APIs, auth, business logic",
        "Builds APIs, business logic, authentication, background jobs, and third-party integrations.",
        ("Claude API", "Code executor", "GitHub MCP", "Postman/API tester"),
        ("REST/GraphQL APIs", "Auth system", "Background workers", "3rd-party integrations"),
        "Database Agent, QA & Testing, Code Reviewer", "backend_plan", "database",
    ),
    AgentId.database_agent: AgentConfig(
        AgentId.database_agent, 8, "Database Agent", "Phase 3 - Development",
        "Schemas, migrations, queries",
        "Designs schemas, migrations, optimized queries, seed data, and index strategy.",
        ("Claude API", "SQL runner", "Prisma/Drizzle MCP", "Redis client"),
        ("DB schema", "Migrations", "Seed data", "Index strategy"),
        "Backend Dev, QA & Testing", "database_plan", "testing",
    ),
    AgentId.qa_agent: AgentConfig(
        AgentId.qa_agent, 9, "QA & Testing", "Phase 4 - Quality & security",
        "Unit, E2E, regression",
        "Generates and runs unit, integration, and regression tests, then reports failures to responsible agents.",
        ("Claude API", "Jest/Vitest runner", "Coverage reporter"),
        ("Unit test suite", "Integration test suite", "Coverage report", "Bug report"),
        "Code Reviewer, Frontend Dev, Backend Dev", "test_results", "review",
    ),
    AgentId.code_reviewer: AgentConfig(
        AgentId.code_reviewer, 10, "Code Reviewer", "Phase 4 - Quality & security",
        "PR reviews, standards",
        "Reviews code quality, architecture alignment, maintainability, and performance anti-patterns.",
        ("Claude API", "GitHub MCP", "ESLint runner", "SonarQube MCP"),
        ("Review comments", "Quality score", "Refactor suggestions", "Approval or rejection"),
        "Security Agent, DevOps Agent", "review_feedback", "security",
    ),
    AgentId.security_agent: AgentConfig(
        AgentId.security_agent, 11, "Security Agent", "Phase 4 - Quality & security",
        "OWASP, auth, vulns",
        "Checks auth flows, input handling, dependency CVEs, secrets management, and API rate limits.",
        ("Claude API", "Snyk MCP", "OWASP checker", "Secrets scanner"),
        ("Security audit report", "CVE list", "Auth review", "Fix recommendations"),
        "DevOps Agent, Backend Dev", "security_report", "deployment",
    ),
    AgentId.devops_agent: AgentConfig(
        AgentId.devops_agent, 12, "DevOps Agent", "Phase 5 - Deployment & docs",
        "CI/CD, Docker, cloud",
        "Creates deployment plans, CI/CD pipelines, Docker files, cloud config, and environment variable guidance.",
        ("Claude API", "GitHub Actions MCP", "Docker runner", "Terraform/Pulumi"),
        ("CI/CD pipeline", "Dockerfile", "K8s manifests", "Cloud infra config"),
        "Monitor & Maintenance, Docs Writer", "deployment_config", "docs",
    ),
    AgentId.docs_writer: AgentConfig(
        AgentId.docs_writer, 13, "Docs Writer", "Phase 5 - Deployment & docs",
        "README, API docs, guides",
        "Generates documentation from code, API specs, and architecture diagrams.",
        ("Claude API", "Docs store", "OpenAPI renderer", "Markdown publisher"),
        ("README.md", "API reference", "User guide", "Changelog"),
        "Monitor & Maintenance", "docs", "monitoring",
    ),
    AgentId.monitor_agent: AgentConfig(
        AgentId.monitor_agent, 15, "Monitor & Maintenance", "Phase 6 - Monitoring & maintenance",
        "Uptime, alerts, feedback loop",
        "Detects incidents, dependency updates, security patches, feedback, and re-queues bugs into fix sprints.",
        ("Claude API", "Sentry MCP", "PagerDuty MCP", "Dependabot runner"),
        ("Incident alerts", "Bug tickets", "Dependency update PRs", "Feedback summaries"),
        "Project Manager, QA, Backend Dev", "incidents", "completed",
    ),
}


def serializable_catalog() -> list[dict[str, object]]:
    return [
        {
            "id": config.id.value,
            "number": config.number,
            "name": config.name,
            "phase": config.phase,
            "short": config.short,
            "role": config.role,
            "tools": list(config.tools),
            "outputs": list(config.outputs),
            "sends": config.sends,
        }
        for config in AGENT_CONFIGS.values()
    ]

