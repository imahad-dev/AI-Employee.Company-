"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Archive,
  BookOpen,
  Check,
  ChevronDown,
  ChevronsRight,
  Clock3,
  Cpu,
  GitPullRequest,
  Hammer,
  HelpCircle,
  KeyRound,
  LayoutDashboard,
  Play,
  RefreshCcw,
  Rocket,
  ShieldCheck,
  Sparkles,
  X
} from "lucide-react";
import {
  API_BASE,
  Agent,
  AuditLog,
  Approval,
  ApprovalPolicy,
  Connector,
  GitHubPreflight,
  GitHubPullRequest,
  GitHubPullRequestStatus,
  GitHubStatus,
  SecretStatus,
  Project,
  ProviderProfile,
  ProviderStatus,
  RepositorySettings,
  RunEvent,
  WorkspaceFile,
  approve,
  buildAgent,
  createProject,
  createGitHubRepository,
  createGitHubPullRequest,
  exportProjectUrl,
  fetchAgents,
  fetchConnectors,
  fetchGitHubPreflight,
  fetchGitHubPullRequestStatus,
  fetchProjectAudit,
  fetchProjects,
  fetchProviders,
  fetchWorkspace,
  fetchWorkspaceFile,
  getGitHubStatus,
  getProject,
  getProviderStatus,
  getSecretStatus,
  loadOperatorKey,
  reject,
  saveGitHubCredentials,
  saveOperatorKey,
  saveProjectCredentials,
  startProject,
  updateProjectPolicy,
  updateProjectRepository,
  updateConnectorSettings
} from "@/lib/api";
import { ActivitySidebar } from "@/components/ActivitySidebar";
import { CommandCenter } from "@/components/CommandCenter";
import { HeroBand } from "@/components/HeroBand";
import { OverviewMetrics } from "@/components/OverviewMetrics";
import { ProjectGallery } from "@/components/ProjectGallery";
import { WorkflowExperience } from "@/components/WorkflowExperience";
import { friendlyPhase, phases, templates } from "@/components/project-data";

export default function Home() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [providers, setProviders] = useState<ProviderProfile[]>([]);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedArtifactIndex, setSelectedArtifactIndex] = useState(0);
  const [project, setProject] = useState<Project | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFile[]>([]);
  const [workspaceRoot, setWorkspaceRoot] = useState("");
  const [selectedWorkspacePath, setSelectedWorkspacePath] = useState("");
  const [selectedWorkspaceContent, setSelectedWorkspaceContent] = useState("");
  const [repositoryProvider, setRepositoryProvider] = useState<RepositorySettings["provider"]>("local");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("main");
  const [workingBranch, setWorkingBranch] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubStatus, setGithubStatus] = useState<GitHubStatus | null>(null);
  const [githubPreflight, setGithubPreflight] = useState<GitHubPreflight | null>(null);
  const [pullRequestStatus, setPullRequestStatus] = useState<GitHubPullRequestStatus | null>(null);
  const [pullRequestTitle, setPullRequestTitle] = useState("");
  const [pullRequestBody, setPullRequestBody] = useState("");
  const [pullRequestResult, setPullRequestResult] = useState<GitHubPullRequest | null>(null);
  const [newRepositoryName, setNewRepositoryName] = useState("ai-powered-employees");
  const [newRepositoryDescription, setNewRepositoryDescription] = useState("Autonomous AI software company platform");
  const [newRepositoryPrivate, setNewRepositoryPrivate] = useState(true);
  const [brief, setBrief] = useState(templates[0].brief);
  const [projectType, setProjectType] = useState(templates[0].type);
  const [providerMode, setProviderMode] = useState("mock");
  const [modelName, setModelName] = useState("");
  const [providerApiKey, setProviderApiKey] = useState("");
  const [providerBaseUrl, setProviderBaseUrl] = useState("");
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [secretStatus, setSecretStatus] = useState<SecretStatus | null>(null);
  const [operatorKey, setOperatorKey] = useState("");
  const [timeline, setTimeline] = useState(templates[0].timeline);
  const [stack, setStack] = useState(templates[0].stack);
  const [activeTemplate, setActiveTemplate] = useState(templates[0].id);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showPipeline, setShowPipeline] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setOperatorKey(loadOperatorKey());
    fetchAgents()
      .then((data) => {
        setAgents(data.agents);
        setSelectedAgentId(data.agents[0]?.id ?? null);
      })
      .catch((err: unknown) => setError(String(err)));
    fetchProviders()
      .then((data) => {
        setProviders(data.providers);
        setProviderMode(data.active_provider || "mock");
      })
      .catch(() => undefined);
    fetchConnectors()
      .then((data) => setConnectors(data.connectors))
      .catch(() => undefined);
    loadProjects();
  }, []);

  useEffect(() => {
    if (!project) return;
    const source = new EventSource(`${API_BASE}/api/projects/${project.project_id}/events`);
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as RunEvent;
      setEvents((existing) => [...existing, event].slice(-80));
      getProject(project.project_id).then((data) => setProject(data.project)).catch(() => undefined);
    };
    source.onerror = () => source.close();
    return () => source.close();
  }, [project?.project_id]);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0],
    [agents, selectedAgentId]
  );
  const selectedProvider = providers.find((provider) => provider.id === providerMode);
  const pendingApprovals = project?.approvals.filter((approval) => approval.status === "pending") ?? [];
  const progress = project ? Math.round((project.completed_agents.length / 14) * 100) : 0;
  const recentEvents = events.slice(-6).reverse();
  const selectedArtifact = project?.artifacts[selectedArtifactIndex];
  const pendingPolicy = project?.approval_policy;

  async function loadProjects() {
    try {
      const result = await fetchProjects();
      setProjects(result.projects);
    } catch {
      setProjects([]);
    }
  }

  function applyTemplate(templateId: string) {
    const template = templates.find((item) => item.id === templateId);
    if (!template) return;
    setActiveTemplate(template.id);
    setBrief(template.brief);
    setProjectType(template.type);
    setTimeline(template.timeline);
    setStack(template.stack);
  }

  async function handleCreate(startAfterCreate = false) {
    setBusy(true);
    setError(null);
    try {
      const result = await createProject({
        project_type: projectType,
        client_brief: brief,
        timeline,
        stack_preferences: stack,
        provider_mode: providerMode,
        model_name: modelName || undefined,
        provider_api_key: providerApiKey || undefined,
        provider_base_url: providerBaseUrl || undefined
      });
      setProject(result.project);
      hydrateRepository(result.project);
      await refreshProviderStatus(result.project.project_id);
      await refreshGitHubStatus(result.project.project_id);
      await loadProjects();
      setEvents([]);
      if (startAfterCreate) {
        const started = await startProject(result.project.project_id);
        setProject(started.project);
        hydrateRepository(started.project);
        await refreshProviderStatus(started.project.project_id);
        await refreshGitHubStatus(started.project.project_id);
        await loadProjects();
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const result = await startProject(project.project_id);
      setProject(result.project);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggleConnector(connector: Connector, enabled: boolean) {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const result = await updateConnectorSettings(project.project_id, {
        connector_id: connector.id,
        enabled,
        allowed_capabilities: enabled ? connector.capabilities.map((capability) => capability.id) : []
      });
      setProject(result.project);
      await loadProjects();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function refreshProject() {
    if (!project) return;
    const result = await getProject(project.project_id);
    setProject(result.project);
    hydrateRepository(result.project);
    await loadProjects();
    await refreshProviderStatus(result.project.project_id);
    await refreshWorkspace(result.project.project_id);
    await refreshGitHubStatus(result.project.project_id);
    await refreshPullRequestStatus(result.project.project_id);
  }

  async function refreshProviderStatus(projectId: string) {
    try {
      const status = await getProviderStatus(projectId);
      setProviderStatus(status);
      const secrets = await getSecretStatus(projectId);
      setSecretStatus(secrets);
    } catch {
      setProviderStatus(null);
      setSecretStatus(null);
    }
  }

  function handleSaveOperatorKey() {
    saveOperatorKey(operatorKey);
  }

  async function refreshGitHubStatus(projectId: string) {
    try {
      const status = await getGitHubStatus(projectId);
      setGithubStatus(status);
      const preflight = await fetchGitHubPreflight(projectId);
      setGithubPreflight(preflight);
    } catch {
      setGithubStatus(null);
      setGithubPreflight(null);
    }
  }

  async function refreshPullRequestStatus(projectId: string) {
    try {
      const result = await fetchGitHubPullRequestStatus(projectId);
      setPullRequestStatus(result.pull_request_status);
    } catch {
      setPullRequestStatus(null);
    }
  }

  async function refreshAudit(projectId: string) {
    try {
      const result = await fetchProjectAudit(projectId);
      setAuditLogs(result.audit_logs);
    } catch {
      setAuditLogs([]);
    }
  }

  async function openProject(projectId: string) {
    setBusy(true);
    setError(null);
    try {
      const result = await getProject(projectId);
      setProject(result.project);
      hydrateRepository(result.project);
      setSelectedArtifactIndex(0);
      setEvents([]);
      await refreshProviderStatus(projectId);
      await refreshGitHubStatus(projectId);
      await refreshPullRequestStatus(projectId);
      await refreshAudit(projectId);
      await refreshWorkspace(projectId);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  function hydrateRepository(nextProject: Project) {
    setRepositoryProvider(nextProject.repository?.provider ?? "local");
    setRepositoryUrl(nextProject.repository?.repository_url ?? "");
    setDefaultBranch(nextProject.repository?.default_branch ?? "main");
    setWorkingBranch(nextProject.repository?.working_branch ?? "");
  }

  async function refreshWorkspace(projectId: string) {
    try {
      const result = await fetchWorkspace(projectId);
      setWorkspaceRoot(result.root);
      setWorkspaceFiles(result.files);
      if (result.files.length === 0) {
        setSelectedWorkspacePath("");
        setSelectedWorkspaceContent("");
      }
    } catch {
      setWorkspaceRoot("");
      setWorkspaceFiles([]);
    }
  }

  async function openWorkspaceFile(path: string) {
    if (!project) return;
    const result = await fetchWorkspaceFile(project.project_id, path);
    setSelectedWorkspacePath(path);
    setSelectedWorkspaceContent(result.content);
  }

  async function saveRepositorySettings() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const result = await updateProjectRepository(project.project_id, {
        provider: repositoryProvider,
        repository_url: repositoryUrl || undefined,
        default_branch: defaultBranch || "main",
        working_branch: workingBranch || undefined
      });
      setProject(result.project);
      hydrateRepository(result.project);
      await refreshAudit(project.project_id);
      await refreshGitHubStatus(project.project_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function togglePolicy(key: keyof ApprovalPolicy) {
    if (!project) return;
    const nextPolicy = { ...project.approval_policy, [key]: !project.approval_policy[key] };
    setBusy(true);
    setError(null);
    try {
      const result = await updateProjectPolicy(project.project_id, nextPolicy);
      setProject(result.project);
      await refreshAudit(project.project_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveCredentials() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const status = await saveProjectCredentials(project.project_id, {
        provider_api_key: providerApiKey || undefined,
        provider_base_url: providerBaseUrl || undefined
      });
      setProviderStatus(status);
      setProviderApiKey("");
      await refreshAudit(project.project_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveGitHubToken() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const status = await saveGitHubCredentials(project.project_id, { github_token: githubToken || undefined });
      setGithubStatus(status);
      setGithubToken("");
      await refreshAudit(project.project_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateRepository() {
    if (!project || !newRepositoryName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await createGitHubRepository(project.project_id, {
        name: newRepositoryName.trim(),
        description: newRepositoryDescription || undefined,
        private: newRepositoryPrivate
      });
      setProject(result.project);
      hydrateRepository(result.project);
      await refreshGitHubStatus(project.project_id);
      await refreshAudit(project.project_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreatePullRequest() {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const result = await createGitHubPullRequest(project.project_id, {
        title: pullRequestTitle || undefined,
        body: pullRequestBody || undefined,
        branch: workingBranch || undefined
      });
      setPullRequestResult(result.pull_request);
      await refreshGitHubStatus(project.project_id);
      await refreshPullRequestStatus(project.project_id);
      await refreshAudit(project.project_id);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleBuildAgent(agentId: string) {
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      await buildAgent(project.project_id, agentId);
      await refreshProject();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function resolveApproval(approvalItem: Approval, accepted: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (accepted) await approve(approvalItem.approval_id);
      else await reject(approvalItem.approval_id);
      await refreshProject();
      if (project) {
        await refreshWorkspace(project.project_id);
        await refreshGitHubStatus(project.project_id);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <HeroBand project={project} pendingApprovals={pendingApprovals} />

      <div className="mission-shell">
        <WorkflowExperience project={project} />
      </div>

      <section className="workspace-grid">
        <aside className="setup-column">
          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="section-title">1. Pick a starting point</p>
                <h2>Project setup</h2>
              </div>
              <LayoutDashboard size={20} />
            </div>

            <div className="template-grid">
              {templates.map((template) => (
                <button
                  key={template.id}
                  className={`template-card ${activeTemplate === template.id ? "active" : ""}`}
                  onClick={() => applyTemplate(template.id)}
                >
                  <strong>{template.title}</strong>
                  <span>{template.timeline}</span>
                </button>
              ))}
            </div>

            <div className="field">
              <label htmlFor="brief">Tell the AI company what to build</label>
              <textarea id="brief" value={brief} onChange={(event) => setBrief(event.target.value)} />
            </div>

            <div className="compact-fields">
              <div className="field">
                <label htmlFor="type">Type</label>
                <select id="type" value={projectType} onChange={(event) => setProjectType(event.target.value)}>
                  <option value="webapp">Web app</option>
                  <option value="dashboard">Dashboard</option>
                  <option value="game">Game</option>
                  <option value="system">System</option>
                  <option value="workflow">Workflow</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="timeline">Timeline</label>
                <input id="timeline" value={timeline} onChange={(event) => setTimeline(event.target.value)} />
              </div>
            </div>

            <button className="advanced-toggle" onClick={() => setShowAdvanced((value) => !value)}>
              <Cpu size={15} /> Model and stack settings <ChevronDown size={15} className={showAdvanced ? "rotate" : ""} />
            </button>

            {showAdvanced && (
              <div className="advanced-box">
                <div className="field">
                  <label htmlFor="stack">Stack preferences</label>
                  <input id="stack" value={stack} onChange={(event) => setStack(event.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="provider">Model provider</label>
                  <select id="provider" value={providerMode} onChange={(event) => setProviderMode(event.target.value)}>
                    {providers.map((provider) => (
                      <option key={provider.id} value={provider.id}>{provider.name}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="model">Model override</label>
                  <input
                    id="model"
                    placeholder={selectedProvider?.default_model ?? "provider default"}
                    value={modelName}
                    onChange={(event) => setModelName(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="api-key">API key for this project</label>
                  <input
                    id="api-key"
                    type="password"
                    placeholder={providerMode === "mock" || providerMode === "local" ? "Usually not needed" : "Paste API key"}
                    value={providerApiKey}
                    onChange={(event) => setProviderApiKey(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="base-url">Base URL override</label>
                  <input
                    id="base-url"
                    placeholder={providerMode === "local" ? "http://localhost:11434/v1" : "Optional custom endpoint"}
                    value={providerBaseUrl}
                    onChange={(event) => setProviderBaseUrl(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="operator-key">Operator API key</label>
                  <input
                    id="operator-key"
                    type="password"
                    placeholder="Only needed when OPERATOR_API_KEY is enabled"
                    value={operatorKey}
                    onChange={(event) => setOperatorKey(event.target.value)}
                  />
                </div>
                <button disabled={busy} onClick={handleSaveOperatorKey}>Save operator key locally</button>
                {selectedProvider && (
                  <p className="hint">
                    {selectedProvider.kind}. {selectedProvider.notes}
                    {selectedProvider.env_keys.length ? ` Needs ${selectedProvider.env_keys.join(", ")} or a key pasted here.` : ""}
                  </p>
                )}
                {project && (
                  <div className={providerStatus?.ready ? "ready-box" : "warning-box"}>
                    <strong>{providerStatus?.ready ? "Provider ready" : "Provider needs setup"}</strong>
                    <span>{providerStatus?.message ?? "Save credentials to check readiness."} {secretStatus?.provider_api_key ? "Encrypted project key stored." : ""}</span>
                    <button disabled={busy} onClick={handleSaveCredentials}>Save credentials</button>
                  </div>
                )}
              </div>
            )}

            <div className="action-row">
              <button className="primary wide" disabled={busy || brief.trim().length < 10} onClick={() => handleCreate(true)}>
                <Rocket size={16} /> Create and run
              </button>
              <button disabled={busy || brief.trim().length < 10} onClick={() => handleCreate(false)}>Save draft</button>
            </div>
            {error && <div className="error-box"><AlertCircle size={15} /> {error}</div>}
          </div>

          <ProjectGallery
            projects={projects}
            activeProjectId={project?.project_id}
            onOpenProject={openProject}
          />
        </aside>

        <section className="main-column">
          <OverviewMetrics project={project} pendingApprovals={pendingApprovals} />

          <CommandCenter
            project={project}
            pendingApprovals={pendingApprovals}
            busy={busy}
            onStart={handleStart}
            onRefresh={refreshProject}
          />

          <div className="panel workflow-upgrade">
            <div className="panel-head">
              <div>
                <p className="section-title">Workflow intelligence</p>
                <h2>Built-in safety and realism</h2>
              </div>
              <ShieldCheck size={20} />
            </div>
            <div className="workflow-grid">
              <div><strong>Preflight</strong><span>Checks provider readiness before real model runs.</span></div>
              <div><strong>Approval gates</strong><span>Files, commands, commits, and deployment plans wait for review.</span></div>
              <div><strong>Memory control</strong><span>Summaries keep long projects cheaper and more focused.</span></div>
              <div><strong>Exportable work</strong><span>Download the project state, approvals, events, and artifacts.</span></div>
              <div><strong>Quality retries</strong><span>Weak agent outputs are scored, corrected, and retried before handoff.</span></div>
              <div><strong>Encrypted keys</strong><span>Project provider and GitHub tokens are stored encrypted at rest.</span></div>
            </div>
          </div>

          {project && pendingPolicy && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <p className="section-title">Enterprise controls</p>
                  <h2>Approval policy</h2>
                </div>
                <ShieldCheck size={20} />
              </div>
              <div className="policy-grid">
                <label><input type="checkbox" checked={pendingPolicy.require_file_write_approval} onChange={() => togglePolicy("require_file_write_approval")} /> File writes need approval</label>
                <label><input type="checkbox" checked={pendingPolicy.require_dependency_approval} onChange={() => togglePolicy("require_dependency_approval")} /> Dependency installs need approval</label>
                <label><input type="checkbox" checked={pendingPolicy.require_shell_approval} onChange={() => togglePolicy("require_shell_approval")} /> Shell commands need approval</label>
                <label><input type="checkbox" checked={pendingPolicy.require_commit_approval} onChange={() => togglePolicy("require_commit_approval")} /> Commits need approval</label>
                <label><input type="checkbox" checked={pendingPolicy.require_deployment_approval} onChange={() => togglePolicy("require_deployment_approval")} /> Deployment needs approval</label>
                <label><input type="checkbox" checked={pendingPolicy.block_on_provider_not_ready} onChange={() => togglePolicy("block_on_provider_not_ready")} /> Block if provider is not ready</label>
              </div>
            </div>
          )}

          {project && connectors.length > 0 && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <p className="section-title">Connected capabilities</p>
                  <h2>Choose what this project can use</h2>
                </div>
                <Cpu size={20} />
              </div>
              <p className="hint">Research and drafting can run automatically. Any change to an external service always enters the approval queue first.</p>
              <div className="connector-grid">
                {connectors.map((connector) => {
                  const setting = project.connector_settings?.[connector.id];
                  const enabled = Boolean(setting?.enabled);
                  const access = connector.capabilities.some((capability) => capability.risk === "write" || capability.risk === "destructive") ? "Approval required for changes" : "Read-only";
                  return (
                    <label className={`connector-item ${enabled ? "enabled" : ""}`} key={connector.id}>
                      <input type="checkbox" checked={enabled} disabled={busy || connector.id === "governance"} onChange={(event) => toggleConnector(connector, event.target.checked)} />
                      <span>
                        <strong>{connector.name}</strong>
                        <small>{connector.description}</small>
                        <em>{connector.id === "governance" ? "Always on for budget protection" : access}</em>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {project && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <p className="section-title">Code delivery</p>
                  <h2>Repository workspace</h2>
                </div>
                <Archive size={20} />
              </div>
              <div className="repo-grid">
                <div className="field">
                  <label htmlFor="repo-provider">Repository provider</label>
                  <select id="repo-provider" value={repositoryProvider} onChange={(event) => setRepositoryProvider(event.target.value as RepositorySettings["provider"])}>
                    <option value="local">Local workspace</option>
                    <option value="github">GitHub</option>
                    <option value="gitlab">GitLab</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="repo-url">Repository URL</label>
                  <input id="repo-url" value={repositoryUrl} onChange={(event) => setRepositoryUrl(event.target.value)} placeholder="Optional for local workspace" />
                </div>
                <div className="field">
                  <label htmlFor="default-branch">Default branch</label>
                  <input id="default-branch" value={defaultBranch} onChange={(event) => setDefaultBranch(event.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="working-branch">Working branch</label>
                  <input id="working-branch" value={workingBranch} onChange={(event) => setWorkingBranch(event.target.value)} placeholder="feature/ai-company-run" />
                </div>
              </div>
              <div className="action-row">
                <button disabled={busy} onClick={saveRepositorySettings}>Save repository settings</button>
                <button disabled={busy} onClick={() => refreshWorkspace(project.project_id)}>Refresh files</button>
              </div>
              <p className="hint">Current workspace: {workspaceRoot || "created when the first file is approved"}. GitHub PR creation unlocks when provider, token, repository URL, and approved files are ready.</p>
            </div>
          )}

          {project && (
            <div className="panel github-panel">
              <div className="panel-head">
                <div>
                  <p className="section-title">GitHub workflow</p>
                  <h2>Create a pull request</h2>
                </div>
                <GitPullRequest size={20} />
              </div>
              <div className="status-checks">
                <div className={`status-check ${repositoryProvider === "github" ? "ready" : ""}`}><Check size={14} /> GitHub provider</div>
                <div className={`status-check ${repositoryUrl ? "ready" : ""}`}><Check size={14} /> Repository URL</div>
                <div className={`status-check ${githubStatus?.has_token ? "ready" : ""}`}><KeyRound size={14} /> Runtime token</div>
                <div className={`status-check ${(githubStatus?.workspace_file_count ?? workspaceFiles.length) > 0 ? "ready" : ""}`}><Archive size={14} /> Approved files</div>
              </div>
              <p className="hint">{githubStatus?.message ?? "Save repository settings and a GitHub token to enable PR creation."}</p>
              <div className="repo-create-box">
                <div className="panel-head compact-head">
                  <div>
                    <strong>Create a GitHub repo</strong>
                    <span>Use the saved token to create a private repo and connect this project automatically.</span>
                  </div>
                </div>
                <div className="github-grid">
                  <div className="field">
                    <label htmlFor="new-repo-name">Repository name</label>
                    <input id="new-repo-name" value={newRepositoryName} onChange={(event) => setNewRepositoryName(event.target.value)} />
                  </div>
                  <div className="field">
                    <label htmlFor="new-repo-description">Description</label>
                    <input id="new-repo-description" value={newRepositoryDescription} onChange={(event) => setNewRepositoryDescription(event.target.value)} />
                  </div>
                </div>
                <div className="action-row">
                  <label className="inline-check"><input type="checkbox" checked={newRepositoryPrivate} onChange={() => setNewRepositoryPrivate((value) => !value)} /> Private repo</label>
                  <button disabled={busy || !githubStatus?.has_token || !newRepositoryName.trim()} onClick={handleCreateRepository}><GitPullRequest size={15} /> Create repo</button>
                </div>
              </div>

              {githubPreflight && (
                <div className="merge-readiness">
                  <div>
                    <strong>PR preflight</strong>
                    <span>{githubPreflight.message}</span>
                  </div>
                  <div className="readiness-list">
                    {githubPreflight.checks.map((check) => (
                      <div key={check.name} className={`readiness-item ${check.passed ? "ready" : ""}`}>
                        {check.passed ? <Check size={14} /> : <AlertCircle size={14} />}
                        {check.name}
                      </div>
                    ))}
                  </div>
                  <details>
                    <summary>Reviewer-ready PR summary</summary>
                    <div className="pre">{githubPreflight.summary}</div>
                  </details>
                </div>
              )}

              <div className="github-grid">
                <div className="field">
                  <label htmlFor="github-token">GitHub token</label>
                  <input id="github-token" type="password" value={githubToken} onChange={(event) => setGithubToken(event.target.value)} placeholder="Stored in memory only" />
                </div>
                <div className="field">
                  <label htmlFor="pr-title">PR title</label>
                  <input id="pr-title" value={pullRequestTitle} onChange={(event) => setPullRequestTitle(event.target.value)} placeholder={`AI company output for ${project.project_id}`} />
                </div>
                <div className="field">
                  <label htmlFor="pr-body">PR notes</label>
                  <textarea id="pr-body" value={pullRequestBody} onChange={(event) => setPullRequestBody(event.target.value)} placeholder="Optional summary for reviewers" />
                </div>
              </div>
              <div className="action-row">
                <button disabled={busy || !githubToken} onClick={handleSaveGitHubToken}><KeyRound size={15} /> Save token</button>
                <button disabled={busy} onClick={() => refreshGitHubStatus(project.project_id)}><RefreshCcw size={15} /> Check readiness</button>
                <button disabled={busy || !githubStatus?.ready} onClick={handleCreatePullRequest}><GitPullRequest size={15} /> Create GitHub PR</button>
                <button disabled={busy || !githubStatus?.has_token} onClick={() => refreshPullRequestStatus(project.project_id)}><RefreshCcw size={15} /> Refresh PR status</button>
              </div>
              {pullRequestResult && (
                <div className="pr-result">
                  <strong>Pull request created</strong>
                  <span>{pullRequestResult.repository} - {pullRequestResult.branch} into {pullRequestResult.base_branch}</span>
                  {pullRequestResult.url && <a href={pullRequestResult.url} target="_blank" rel="noreferrer">{pullRequestResult.url}</a>}
                </div>
              )}
              {pullRequestStatus && (
                <div className={`merge-readiness ${pullRequestStatus.merge_ready ? "ready" : ""}`}>
                  <div>
                    <strong>{pullRequestStatus.merge_ready ? "Merge-ready" : "Needs review"}</strong>
                    <span>{pullRequestStatus.message}</span>
                  </div>
                  <div className="readiness-list">
                    <div className={`readiness-item ${pullRequestStatus.state === "open" ? "ready" : ""}`}>State: {pullRequestStatus.state ?? "unknown"}</div>
                    <div className={`readiness-item ${pullRequestStatus.mergeable !== false ? "ready" : ""}`}>Mergeable: {String(pullRequestStatus.mergeable ?? "pending")}</div>
                    <div className={`readiness-item ${pullRequestStatus.checks.every((check) => check.conclusion === "success" || check.conclusion === "skipped" || check.conclusion === "neutral") ? "ready" : ""}`}>Checks: {pullRequestStatus.checks.length}</div>
                    <div className={`readiness-item ${pullRequestStatus.review_summary.changes_requested === 0 ? "ready" : ""}`}>Reviews: {pullRequestStatus.review_summary.approved} approved</div>
                  </div>
                  <span className="hint">{pullRequestStatus.file_count} changed files on {pullRequestStatus.head_branch} into {pullRequestStatus.base_branch}</span>
                </div>
              )}
            </div>
          )}

          {pendingApprovals.length > 0 && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <p className="section-title">3. Review before anything changes</p>
                  <h2>Approval inbox</h2>
                </div>
                <ShieldCheck size={20} />
              </div>
              <div className="approval-list">
                {pendingApprovals.map((approvalItem) => (
                  <div key={approvalItem.approval_id} className="approval">
                    <strong>{approvalItem.title}</strong>
                    <span>{approvalItem.kind} from {approvalItem.agent_id}</span>
                    <details>
                      <summary>Preview proposed change</summary>
                      {typeof approvalItem.payload.diff === "string" && approvalItem.payload.diff && (
                        <div className="diff-box">{approvalItem.payload.diff}</div>
                      )}
                      <div className="pre">{JSON.stringify(approvalItem.payload, null, 2)}</div>
                    </details>
                    <div className="action-row">
                      <button disabled={busy} onClick={() => resolveApproval(approvalItem, true)}><Check size={15} /> Approve</button>
                      <button disabled={busy} onClick={() => resolveApproval(approvalItem, false)}><X size={15} /> Reject</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="section-title">Results</p>
                <h2>Artifacts and downloads</h2>
              </div>
              {project && (
                <a className="button-link" href={exportProjectUrl(project.project_id)}>
                  <Archive size={15} /> Export ZIP
                </a>
              )}
            </div>
            {!project && <p className="muted">Create or open a project to see generated code, docs, plans, and approval-ready outputs.</p>}
            {project && project.artifacts.length === 0 && (
              <p className="muted">Artifacts will appear here as the AI employees generate frontend, backend, docs, and deployment outputs.</p>
            )}
            {project && project.artifacts.length > 0 && (
              <div className="artifact-browser">
                <div className="artifact-list">
                  {project.artifacts.map((artifact, index) => (
                    <button
                      key={artifact.artifact_id}
                      className={`artifact-row ${selectedArtifactIndex === index ? "active" : ""}`}
                      onClick={() => setSelectedArtifactIndex(index)}
                    >
                      <strong>{artifact.name}</strong>
                      <span>{artifact.kind} from {artifact.agent_id}</span>
                    </button>
                  ))}
                </div>
                <div className="artifact-preview">
                  <strong>{selectedArtifact?.name}</strong>
                  <span>{selectedArtifact?.kind}</span>
                  <div className="pre">{JSON.stringify(selectedArtifact?.content, null, 2)}</div>
                </div>
              </div>
            )}
          </div>

          {project && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <p className="section-title">Workspace files</p>
                  <h2>Approved code output</h2>
                </div>
                <button disabled={busy} onClick={() => refreshWorkspace(project.project_id)}>Refresh</button>
              </div>
              {workspaceFiles.length === 0 && <p className="muted">Approved file writes will appear here. Nothing is written until you approve it.</p>}
              {workspaceFiles.length > 0 && (
                <div className="workspace-browser">
                  <div className="workspace-list">
                    {workspaceFiles.map((file) => (
                      <button
                        key={file.path}
                        className={`workspace-row ${selectedWorkspacePath === file.path ? "active" : ""}`}
                        onClick={() => openWorkspaceFile(file.path)}
                      >
                        <strong>{file.path}</strong>
                        <span>{file.size} bytes</span>
                      </button>
                    ))}
                  </div>
                  <div className="workspace-preview">
                    <strong>{selectedWorkspacePath || "Select a file"}</strong>
                    <div className="pre">{selectedWorkspaceContent || "File content preview will appear here."}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="section-title">Pipeline</p>
                <h2>AI employee board</h2>
              </div>
              <button onClick={() => setShowPipeline((value) => !value)}>
                {showPipeline ? "Hide details" : "Show details"}
              </button>
            </div>

            {showPipeline ? (
              <>
                {phases.map((phase) => {
                  const rowAgents = agents.filter((agent) => agent.phase === phase);
                  if (phase.includes("Monitoring")) {
                    rowAgents.unshift({
                      id: "performance_agent",
                      number: 14,
                      name: "Performance Agent",
                      phase,
                      short: "Deferred to V1.1",
                      role: "Profiles frontend and backend performance. V1 shows a placeholder until the core pipeline is proven.",
                      tools: ["Lighthouse", "Query profiler", "Bundle analyzer"],
                      outputs: ["Static placeholder report"],
                      sends: "Monitor & Maintenance"
                    });
                  }
                  return (
                    <div key={phase}>
                      <div className="phase-label">{phase}</div>
                      <div className="phase-row">
                        {rowAgents.map((agent, index) => (
                          <div key={agent.id} style={{ display: "contents" }}>
                            <button
                              className={`agent-card ${selectedAgentId === agent.id ? "active" : ""} ${project?.completed_agents.includes(agent.id) ? "done" : ""}`}
                              onClick={() => setSelectedAgentId(agent.id)}
                            >
                              <div className="agent-num">{String(agent.number).padStart(2, "0")}</div>
                              <div className="agent-title">{agent.name}</div>
                              <div className="agent-sub">{agent.short}</div>
                            </button>
                            {index < rowAgents.length - 1 && <div className="connector"><ChevronsRight size={16} /></div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}

                {selectedAgent && (
                  <div className="agent-detail">
                    <div>
                      <p className="section-title">Selected employee</p>
                      <h3>{String(selectedAgent.number).padStart(2, "0")} - {selectedAgent.name}</h3>
                      <p className="muted">{selectedAgent.role}</p>
                      <p className="route-note">Sends results to: <strong>{selectedAgent.sends}</strong></p>
                      {project?.agent_quality?.[selectedAgent.id] && (
                        <div className="quality-strip">
                          <span>Quality {project.agent_quality[selectedAgent.id].score ?? "-"} / 10</span>
                          <span>{project.agent_quality[selectedAgent.id].attempts ?? 1} attempt(s)</span>
                          <span>{project.agent_quality[selectedAgent.id].duration_ms ?? 0} ms</span>
                        </div>
                      )}
                    </div>
                    <div>
                      {selectedAgent.tools.map((tool) => <span key={tool} className="tool-pill">{tool}</span>)}
                      <button className="primary wide" disabled={!project || busy || selectedAgent.id === "performance_agent"} onClick={() => handleBuildAgent(selectedAgent.id)}>
                        <Hammer size={15} /> Build this employee
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="simple-stages">
                {["Plan", "Design", "Build", "Test", "Deploy", "Maintain"].map((stage, index) => (
                  <div key={stage} className={progress >= index * 16 ? "stage active" : "stage"}>
                    <span>{index + 1}</span>
                    <strong>{stage}</strong>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <aside className="activity-column">
          <ActivitySidebar project={project} recentEvents={recentEvents} auditLogs={auditLogs} />
        </aside>
      </section>
    </main>
  );
}
