import { Play, RefreshCcw } from "lucide-react";
import { Approval, Project } from "@/lib/api";
import { friendlyPhase, nextAction } from "./project-data";

type CommandCenterProps = {
  project: Project | null;
  pendingApprovals: Approval[];
  busy: boolean;
  onStart: () => void;
  onRefresh: () => void;
};

export function CommandCenter({ project, pendingApprovals, busy, onStart, onRefresh }: CommandCenterProps) {
  return (
    <div className="panel command-center">
      <div>
        <p className="section-title">2. Run the company</p>
        <h2>{project ? friendlyPhase(project.current_phase) : "No project yet"}</h2>
        <p className="muted">{nextAction(project, pendingApprovals)}</p>
      </div>
      <div className="action-row end">
        <button className="primary" disabled={!project || busy || project.status === "running"} onClick={onStart}>
          <Play size={15} /> Start
        </button>
        <button disabled={!project || busy} onClick={onRefresh}><RefreshCcw size={15} /> Refresh</button>
      </div>
    </div>
  );
}
