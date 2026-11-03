import { Approval, Project } from "@/lib/api";

export const phases = [
  "Phase 1 - Intake & planning",
  "Phase 2 - Design",
  "Phase 3 - Development",
  "Phase 4 - Quality & security",
  "Phase 5 - Deployment & docs",
  "Phase 6 - Monitoring & maintenance"
];

export const templates = [
  {
    id: "saas-dashboard",
    title: "SaaS Dashboard",
    type: "dashboard",
    timeline: "4 weeks",
    stack: "Next.js, FastAPI, SQLite now, PostgreSQL-ready later, Vercel deployment plan",
    brief:
      "Build a SaaS analytics dashboard for e-commerce stores. Include sales charts, inventory tracking, customer segments, real-time alerts, CSV export, multi-tenant auth, admin settings, and clean onboarding."
  },
  {
    id: "web-app",
    title: "Customer Web App",
    type: "webapp",
    timeline: "3 weeks",
    stack: "Next.js, Tailwind, FastAPI, approval-gated deployment plan",
    brief:
      "Build a polished customer-facing web app with account creation, dashboard, profile settings, notifications, billing-ready structure, responsive UI, and documentation."
  },
  {
    id: "internal-tool",
    title: "Internal Workflow Tool",
    type: "workflow",
    timeline: "2 weeks",
    stack: "FastAPI, Next.js, SQLite, role-based access, local-first deployment",
    brief:
      "Build an internal workflow tool for a small team. Include task intake, approvals, status tracking, searchable records, exports, admin controls, and audit history."
  },
  {
    id: "game",
    title: "Interactive Game",
    type: "game",
    timeline: "3 weeks",
    stack: "React, TypeScript, canvas or Three.js as needed, local deploy plan",
    brief:
      "Build a browser game with a complete playable loop, score tracking, responsive controls, restart flow, polished visuals, sound-ready hooks, and testing plan."
  }
];

export function friendlyPhase(phase?: string) {
  const map: Record<string, string> = {
    intake: "Planning the work",
    requirements: "Writing requirements",
    architecture: "Designing architecture",
    design: "Designing screens",
    components: "Planning components",
    frontend: "Building frontend",
    backend: "Building backend",
    database: "Preparing data layer",
    testing: "Testing",
    review: "Reviewing code",
    security: "Checking security",
    deployment: "Preparing deployment",
    docs: "Writing docs",
    monitoring: "Preparing maintenance",
    completed: "Completed"
  };
  return map[phase ?? ""] ?? "Ready";
}

export function nextAction(project: Project | null, pendingApprovals: Approval[]) {
  if (!project) return "Choose a template or describe your idea, then create a project.";
  if (pendingApprovals.length) return `${pendingApprovals.length} approval${pendingApprovals.length === 1 ? "" : "s"} waiting for your review.`;
  if (project.status === "paused") return "Project is ready. Start the AI company when you are comfortable.";
  if (project.status === "running") return `${friendlyPhase(project.current_phase)} is in progress.`;
  if (project.status === "completed") return "Pipeline completed. Review artifacts and approval history.";
  return "Something needs attention. Check the activity log.";
}
