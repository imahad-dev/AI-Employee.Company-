export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export type Agent = {
  id: string;
  number: number;
  name: string;
  phase: string;
  short: string;
  role: string;
  tools: string[];
  outputs: string[];
  sends: string;
};

export type Project = {
  project_id: string;
  project_type: string;
  client_brief: string;
  timeline?: string | null;
  stack_preferences?: string | null;
  provider_mode?: string | null;
  model_name?: string | null;
  repository: RepositorySettings;
  current_phase: string;
  active_agent: string;
  completed_agents: string[];
  status: string;
  errors: string[];
  approvals: Approval[];
  approval_policy: ApprovalPolicy;
  artifacts: Artifact[];
  summaries: string[];
  token_usage: {
    input_tokens: number;
    output_tokens: number;
    estimated_cost_usd: number;
  };
};

export type RepositorySettings = {
  provider: "local" | "github" | "gitlab";
  repository_url?: string | null;
  default_branch: string;
  working_branch?: string | null;
};

export type WorkspaceFile = {
  path: string;
  size: number;
  modified: number;
};

export type ApprovalPolicy = {
  require_file_write_approval: boolean;
  require_dependency_approval: boolean;
  require_shell_approval: boolean;
  require_commit_approval: boolean;
  require_deployment_approval: boolean;
  block_on_provider_not_ready: boolean;
  max_auto_loop_count: number;
};

export type Artifact = {
  artifact_id: string;
  project_id: string;
  agent_id: string;
  name: string;
  kind: string;
  content: unknown;
  created_at: string;
};

export type ProviderProfile = {
  id: string;
  name: string;
  kind: string;
  default_model: string;
  env_keys: string[];
  notes: string;
};

export type ProviderStatus = {
  provider: string;
  ready: boolean;
  has_runtime_key: boolean;
  uses_env_key: boolean;
  message: string;
};

export type GitHubStatus = {
  ready: boolean;
  provider: string;
  repository_url?: string | null;
  default_branch: string;
  working_branch?: string | null;
  has_token: boolean;
  workspace_file_count: number;
  message: string;
};

export type GitHubPullRequest = {
  repository: string;
  url?: string | null;
  number?: number | null;
  branch: string;
  base_branch: string;
  files_changed: string[];
};

export type GitHubPreflight = {
  ready: boolean;
  checks: { name: string; passed: boolean }[];
  files: WorkspaceFile[];
  blocked_files: string[];
  large_files: string[];
  pending_approvals: string[];
  summary: string;
  message: string;
};

export type GitHubPullRequestStatus = {
  url?: string | null;
  number?: number | null;
  state?: string | null;
  draft: boolean;
  title?: string | null;
  base_branch?: string | null;
  head_branch?: string | null;
  head_sha?: string | null;
  mergeable?: boolean | null;
  merge_ready: boolean;
  file_count: number;
  changed_files: (string | null | undefined)[];
  checks: { name?: string | null; status?: string | null; conclusion?: string | null }[];
  review_summary: { approved: number; changes_requested: number; total_reviews: number };
  message: string;
};

export type GitHubRepositoryResult = {
  name?: string | null;
  url?: string | null;
  private?: boolean | null;
  default_branch?: string | null;
};

export type Approval = {
  approval_id: string;
  project_id: string;
  agent_id: string;
  kind: string;
  title: string;
  payload: Record<string, unknown>;
  status: "pending" | "approved" | "rejected";
  reviewer_note?: string | null;
};

export type RunEvent = {
  event_id: string;
  project_id: string;
  type: string;
  message: string;
  agent_id?: string | null;
  data: Record<string, unknown>;
  created_at: string;
};

export type AuditLog = {
  audit_id: string;
  project_id?: string | null;
  actor: string;
  action: string;
  target?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export async function fetchAgents() {
  return json<{ agents: Agent[]; performance_agent: { status: string; target: string } }>("/api/agents");
}

export async function fetchProviders() {
  return json<{ active_provider: string; providers: ProviderProfile[]; local_base_url: string }>("/api/providers");
}

export async function createProject(input: {
  project_type: string;
  client_brief: string;
  timeline?: string;
  stack_preferences?: string;
  provider_mode?: string;
  model_name?: string;
  provider_api_key?: string;
  provider_base_url?: string;
}) {
  return json<{ project: Project }>("/api/projects", { method: "POST", body: JSON.stringify(input) });
}

export async function fetchProjects() {
  return json<{ projects: Project[] }>("/api/projects");
}

export async function startProject(projectId: string) {
  return json<{ project: Project }>(`/api/projects/${projectId}/start`, { method: "POST" });
}

export async function getProviderStatus(projectId: string) {
  return json<ProviderStatus>(`/api/projects/${projectId}/provider-status`);
}

export async function saveProjectCredentials(projectId: string, input: { provider_api_key?: string; provider_base_url?: string }) {
  return json<ProviderStatus>(`/api/projects/${projectId}/credentials`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function getGitHubStatus(projectId: string) {
  return json<GitHubStatus>(`/api/projects/${projectId}/github/status`);
}

export async function saveGitHubCredentials(projectId: string, input: { github_token?: string }) {
  return json<GitHubStatus>(`/api/projects/${projectId}/github/credentials`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function fetchGitHubPreflight(projectId: string) {
  return json<GitHubPreflight>(`/api/projects/${projectId}/github/preflight`);
}

export async function createGitHubRepository(projectId: string, input: { name: string; description?: string; private?: boolean }) {
  return json<{ repository: GitHubRepositoryResult; project: Project }>(`/api/projects/${projectId}/github/repository`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function createGitHubPullRequest(projectId: string, input: { title?: string; body?: string; branch?: string }) {
  return json<{ pull_request: GitHubPullRequest }>(`/api/projects/${projectId}/github/pull-request`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function fetchGitHubPullRequestStatus(projectId: string) {
  return json<{ pull_request_status: GitHubPullRequestStatus }>(`/api/projects/${projectId}/github/pull-request/status`);
}

export async function getProject(projectId: string) {
  return json<{ project: Project }>(`/api/projects/${projectId}`);
}

export async function fetchProjectAudit(projectId: string) {
  return json<{ audit_logs: AuditLog[] }>(`/api/projects/${projectId}/audit`);
}

export async function updateProjectPolicy(projectId: string, approvalPolicy: ApprovalPolicy) {
  return json<{ project: Project }>(`/api/projects/${projectId}/policy`, {
    method: "POST",
    body: JSON.stringify({ approval_policy: approvalPolicy })
  });
}

export async function updateProjectRepository(projectId: string, repository: RepositorySettings) {
  return json<{ project: Project }>(`/api/projects/${projectId}/repository`, {
    method: "POST",
    body: JSON.stringify({ repository })
  });
}

export async function fetchWorkspace(projectId: string) {
  return json<{ root: string; files: WorkspaceFile[] }>(`/api/projects/${projectId}/workspace`);
}

export async function fetchWorkspaceFile(projectId: string, path: string) {
  return json<{ path: string; content: string }>(`/api/projects/${projectId}/workspace/file?path=${encodeURIComponent(path)}`);
}

export async function buildAgent(projectId: string, agentId: string) {
  return json<{ approval: Approval }>(`/api/projects/${projectId}/agents/build`, {
    method: "POST",
    body: JSON.stringify({ agent_id: agentId })
  });
}

export async function approve(approvalId: string) {
  return json<{ approval: Approval }>(`/api/approvals/${approvalId}/approve`, { method: "POST" });
}

export async function reject(approvalId: string) {
  return json<{ approval: Approval }>(`/api/approvals/${approvalId}/reject`, {
    method: "POST",
    body: JSON.stringify({ note: "Rejected from dashboard" })
  });
}

export function exportProjectUrl(projectId: string) {
  return `${API_BASE}/api/projects/${projectId}/export`;
}
