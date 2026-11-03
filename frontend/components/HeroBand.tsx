import { Sparkles } from "lucide-react";
import { Approval, Project } from "@/lib/api";
import { friendlyPhase, nextAction } from "./project-data";

type HeroBandProps = {
  project: Project | null;
  pendingApprovals: Approval[];
};

export function HeroBand({ project, pendingApprovals }: HeroBandProps) {
  return (
    <section className="hero-band">
      <div>
        <div className="eyebrow"><Sparkles size={15} /> Autonomous software company</div>
        <h1>Describe the product. The AI team plans, builds, reviews, and prepares it for deployment.</h1>
        <p>
          Start safely in mock mode, then switch the same workflow to Claude, Gemini, Groq, OpenRouter, OpenAI,
          or a local model when you are ready.
        </p>
      </div>
      <div className="hero-card">
        <span className="status-pill">{project?.status ?? "ready"}</span>
        <strong>{friendlyPhase(project?.current_phase)}</strong>
        <p>{nextAction(project, pendingApprovals)}</p>
      </div>
    </section>
  );
}
