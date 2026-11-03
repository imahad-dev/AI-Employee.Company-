import { Approval, Project } from "@/lib/api";

type OverviewMetricsProps = {
  project: Project | null;
  pendingApprovals: Approval[];
};

export function OverviewMetrics({ project, pendingApprovals }: OverviewMetricsProps) {
  const progress = project ? Math.round((project.completed_agents.length / 14) * 100) : 0;

  return (
    <div className="overview-row">
      <div className="metric-card">
        <span>Progress</span>
        <strong>{progress}%</strong>
        <div className="progress-track"><div style={{ width: `${progress}%` }} /></div>
      </div>
      <div className="metric-card">
        <span>Completed agents</span>
        <strong>{project?.completed_agents.length ?? 0}/14</strong>
      </div>
      <div className="metric-card">
        <span>Approvals</span>
        <strong>{pendingApprovals.length}</strong>
      </div>
      <div className="metric-card">
        <span>Estimated cost</span>
        <strong>${project?.token_usage.estimated_cost_usd.toFixed(2) ?? "0.00"}</strong>
      </div>
    </div>
  );
}
