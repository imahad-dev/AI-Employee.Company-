import { BookOpen, Clock3, HelpCircle, ShieldCheck } from "lucide-react";
import { AuditLog, Project, RunEvent } from "@/lib/api";

type ActivitySidebarProps = {
  project: Project | null;
  recentEvents: RunEvent[];
  auditLogs: AuditLog[];
};

export function ActivitySidebar({ project, recentEvents, auditLogs }: ActivitySidebarProps) {
  return (
    <>
      <div className="panel dark-help">
        <div className="panel-head">
          <div>
            <p className="section-title">Beginner guide</p>
            <h2>How to use this</h2>
          </div>
          <HelpCircle size={20} />
        </div>
        <ol className="tutorial-list">
          <li><strong>Pick a template.</strong><span>Start with a common product type so you do not face a blank page.</span></li>
          <li><strong>Edit the brief.</strong><span>Write what the software should do in normal language.</span></li>
          <li><strong>Click Create and run.</strong><span>Mock mode is safe and costs nothing.</span></li>
          <li><strong>Approve changes.</strong><span>The system asks before writing files or deployment plans.</span></li>
          <li><strong>Export results.</strong><span>Download everything as a ZIP when the run is useful.</span></li>
        </ol>
        <p className="key-note">API keys pasted in the interface are used for this local runtime and are not shown back in saved project data.</p>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <p className="section-title">Activity</p>
            <h2>What just happened</h2>
          </div>
          <Clock3 size={20} />
        </div>
        <div className="log">
          {recentEvents.length === 0 && <p className="muted">Activity will appear here after you create and run a project.</p>}
          {recentEvents.map((event) => (
            <div key={event.event_id} className="log-item">
              <strong>{event.message}</strong>
              <span>{event.type}{event.agent_id ? ` from ${event.agent_id}` : ""}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <p className="section-title">Memory control</p>
        <h2>Summaries</h2>
        {project?.summaries.length ? (
          project.summaries.slice(-4).map((summary, index) => <p key={index} className="summary-note">{summary}</p>)
        ) : (
          <p className="muted">The Summarizer compresses context after every 3 completed employees to control cost.</p>
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <p className="section-title">Enterprise audit</p>
            <h2>Decision trail</h2>
          </div>
          <ShieldCheck size={20} />
        </div>
        <div className="audit-list">
          {auditLogs.length === 0 && <p className="muted">Open or run a project to see an audit trail.</p>}
          {auditLogs.slice(0, 8).map((item) => (
            <div key={item.audit_id} className="audit-row">
              <strong>{item.action.replaceAll("_", " ")}</strong>
              <span>{item.actor} - {item.target ?? "project"}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <p className="section-title">Helpful tips</p>
            <h2>Better prompts</h2>
          </div>
          <BookOpen size={20} />
        </div>
        <div className="tips-list">
          <p>Say who will use the app, what screens they need, and what data matters most.</p>
          <p>Keep real deployment in approval mode until credentials and budgets are ready.</p>
          <p>Use local or mock models while testing workflows, then switch providers for quality runs.</p>
        </div>
      </div>
    </>
  );
}
