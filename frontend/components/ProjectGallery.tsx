import { Archive } from "lucide-react";
import { Project } from "@/lib/api";
import { friendlyPhase } from "./project-data";

type ProjectGalleryProps = {
  projects: Project[];
  activeProjectId?: string;
  onOpenProject: (projectId: string) => void;
};

export function ProjectGallery({ projects, activeProjectId, onOpenProject }: ProjectGalleryProps) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <p className="section-title">Saved work</p>
          <h2>Project gallery</h2>
        </div>
        <Archive size={20} />
      </div>
      <div className="project-list">
        {projects.length === 0 && <p className="muted">Saved projects will appear here after you create one.</p>}
        {projects.slice(0, 6).map((item) => (
          <button
            key={item.project_id}
            className={`project-row ${activeProjectId === item.project_id ? "active" : ""}`}
            onClick={() => onOpenProject(item.project_id)}
          >
            <strong>{friendlyPhase(item.current_phase)}</strong>
            <span>{item.project_type} - {item.status}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
