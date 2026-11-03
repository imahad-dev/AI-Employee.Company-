"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, Pause, Play, RotateCcw, Sparkles } from "lucide-react";
import * as THREE from "three";
import { Project } from "@/lib/api";

const stages = [
  {
    id: "plan",
    title: "Plan the mission",
    short: "Plan",
    agents: ["project_manager", "requirements_analyst", "system_architect"],
    outputs: ["Project roadmap", "User stories and acceptance criteria", "Architecture and API plan"],
    demo: "The team turns a product idea into a scoped, buildable plan.",
    color: 0x59d9cc
  },
  {
    id: "design",
    title: "Design the experience",
    short: "Design",
    agents: ["ui_designer", "component_planner"],
    outputs: ["Screen and interaction spec", "Reusable component plan", "Design tokens"],
    demo: "A clear interface and component system are mapped before implementation.",
    color: 0x68b6ff
  },
  {
    id: "build",
    title: "Build the product",
    short: "Build",
    agents: ["frontend_developer", "backend_developer", "database_agent"],
    outputs: ["Frontend implementation", "Backend endpoints", "Database schema"],
    demo: "Frontend, backend, and data work are created as reviewable artifacts.",
    color: 0xb2d96c
  },
  {
    id: "verify",
    title: "Verify quality",
    short: "Verify",
    agents: ["qa_agent", "code_reviewer", "security_agent"],
    outputs: ["Test report", "Code review findings", "Security assessment"],
    demo: "Independent checks find issues before the work moves toward release.",
    color: 0xffc46b
  },
  {
    id: "release",
    title: "Prepare release",
    short: "Release",
    agents: ["devops_agent", "docs_writer"],
    outputs: ["Staging deployment plan", "Operator guide", "Release notes"],
    demo: "Deployment steps and practical documentation are prepared for approval.",
    color: 0xff8f73
  },
  {
    id: "operate",
    title: "Operate and improve",
    short: "Operate",
    agents: ["monitor_agent"],
    outputs: ["Monitoring checklist", "Incident response plan", "Follow-up improvements"],
    demo: "The team closes the loop with monitoring and a path for future fixes.",
    color: 0xc5a1ff
  }
];

const phaseStage: Record<string, number> = {
  intake: 0, requirements: 0, architecture: 0,
  design: 1, components: 1,
  frontend: 2, backend: 2, database: 2,
  testing: 3, review: 3, security: 3,
  deployment: 4, docs: 4,
  monitoring: 5, completed: 5
};

const demoArtifacts = [
  "MarketPulse product brief and four user stories",
  "Analytics dashboard wireframe and component map",
  "Sales API, inventory model, and responsive dashboard",
  "QA results, review notes, and security checklist",
  "Staging release plan and getting-started guide",
  "Alert runbook and next-iteration backlog"
];

type Props = { project: Project | null };

function RoverScene({ activeIndex, completedThrough, onSelect }: { activeIndex: number; completedThrough: number; onSelect: (index: number) => void }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const selectRef = useRef(onSelect);
  const targetIndexRef = useRef(activeIndex);
  const completedRef = useRef(completedThrough);

  useEffect(() => { selectRef.current = onSelect; }, [onSelect]);
  useEffect(() => { targetIndexRef.current = activeIndex; }, [activeIndex]);
  useEffect(() => { completedRef.current = completedThrough; }, [completedThrough]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    camera.position.set(0, 7.2, 13.8);
    camera.lookAt(0, 0, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "low-power" });
    } catch {
      mount.dataset.sceneUnavailable = "true";
      mount.textContent = "3D view unavailable in this browser. Use the stage controls below.";
      return () => {
        mount.textContent = "";
        delete mount.dataset.sceneUnavailable;
      };
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.7));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xd9f5ff, 0x25334e, 2.0));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    keyLight.position.set(-3, 8, 5);
    scene.add(keyLight);
    const rimLight = new THREE.PointLight(0x42c9f5, 12, 18);
    rimLight.position.set(0, 3.2, -1);
    scene.add(rimLight);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(20, 10),
      new THREE.MeshStandardMaterial({ color: 0x111a27, roughness: 0.95, metalness: 0.08 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.42;
    scene.add(ground);

    const grid = new THREE.GridHelper(20, 32, 0x356079, 0x25374a);
    grid.position.y = -0.405;
    const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material];
    gridMaterials.forEach((material) => { material.transparent = true; material.opacity = 0.28; });
    scene.add(grid);

    const positions = stages.map((_, index) => new THREE.Vector3((index - 2.5) * 2.35, 0, Math.sin(index * 0.8) * 0.42));
    const route = new THREE.Mesh(
      new THREE.BufferGeometry(),
      new THREE.MeshStandardMaterial({ color: 0x4f819a, emissive: 0x1f5062, emissiveIntensity: 0.7, metalness: 0.45, roughness: 0.4 })
    );
    const updateRoute = (spread: number) => {
      const curve = new THREE.CatmullRomCurve3(positions.map((position) => new THREE.Vector3(position.x * spread, -0.03, position.z)));
      const previousGeometry = route.geometry;
      route.geometry = new THREE.TubeGeometry(curve, 96, 0.035, 8, false);
      previousGeometry.dispose();
    };
    updateRoute(1);
    scene.add(route);

    const checkpoints: THREE.Group[] = [];
    const rings: THREE.Mesh[] = [];
    stages.forEach((stage, index) => {
      const group = new THREE.Group();
      group.position.copy(positions[index]);

      const platform = new THREE.Mesh(
        new THREE.CylinderGeometry(0.73, 0.9, 0.24, 8),
        new THREE.MeshStandardMaterial({ color: 0x293b4f, roughness: 0.4, metalness: 0.65 })
      );
      platform.position.y = -0.23;
      group.add(platform);

      const center = new THREE.Mesh(
        new THREE.IcosahedronGeometry(0.3, 1),
        new THREE.MeshStandardMaterial({ color: stage.color, emissive: stage.color, emissiveIntensity: 0.28, roughness: 0.26, metalness: 0.3 })
      );
      center.position.y = 0.22;
      group.add(center);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.55, 0.025, 8, 48),
        new THREE.MeshBasicMaterial({ color: stage.color, transparent: true, opacity: 0.52 })
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.y = -0.07;
      group.add(ring);
      rings.push(ring);
      group.userData.stageIndex = index;
      group.userData.center = center;
      checkpoints.push(group);
      scene.add(group);
    });


    const rover = new THREE.Group();
    const chassis = new THREE.Mesh(
      new THREE.BoxGeometry(0.78, 0.34, 0.56),
      new THREE.MeshStandardMaterial({ color: 0xe8f1f5, roughness: 0.3, metalness: 0.72 })
    );
    chassis.position.y = 0.35;
    rover.add(chassis);
    const cockpit = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 16, 12),
      new THREE.MeshStandardMaterial({ color: 0x56d8cf, emissive: 0x1b6b7a, emissiveIntensity: 0.8, roughness: 0.18, metalness: 0.35 })
    );
    cockpit.scale.set(1, 0.62, 1);
    cockpit.position.set(0.04, 0.59, 0);
    rover.add(cockpit);
    const wheelGeometry = new THREE.CylinderGeometry(0.17, 0.17, 0.14, 16);
    const wheelMaterial = new THREE.MeshStandardMaterial({ color: 0x101720, roughness: 0.75, metalness: 0.2 });
    const wheels: THREE.Mesh[] = [];
    for (const x of [-0.27, 0.27]) {
      for (const z of [-0.34, 0.34]) {
        const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(x, 0.21, z);
        rover.add(wheel);
        wheels.push(wheel);
      }
    }
    const beacon = new THREE.Mesh(
      new THREE.SphereGeometry(0.075, 12, 10),
      new THREE.MeshBasicMaterial({ color: 0x82fff4 })
    );
    beacon.position.set(0.3, 0.62, 0);
    rover.add(beacon);
    const roverGlow = new THREE.PointLight(0x5cdbef, 3, 2.4);
    roverGlow.position.set(0, 0.8, 0);
    rover.add(roverGlow);
    scene.add(rover);

    const starsGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(150 * 3);
    for (let i = 0; i < 150; i += 1) {
      starPositions[i * 3] = (Math.random() - 0.5) * 18;
      starPositions[i * 3 + 1] = 1.4 + Math.random() * 4;
      starPositions[i * 3 + 2] = (Math.random() - 0.5) * 11 - 2;
    }
    starsGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    const stars = new THREE.Points(starsGeometry, new THREE.PointsMaterial({ color: 0xa7d5eb, size: 0.028, transparent: true, opacity: 0.72 }));
    scene.add(stars);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const onPointerDown = (event: PointerEvent) => {
      const bounds = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
      pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(checkpoints, true);
      const group = hits.map((hit) => hit.object.parent).find((parent) => parent?.userData.stageIndex !== undefined);
      if (group) selectRef.current(group.userData.stageIndex as number);
    };
    renderer.domElement.addEventListener("pointerdown", onPointerDown);

    const resizeObserver = new ResizeObserver(() => {
      const width = Math.max(mount.clientWidth, 1);
      const height = Math.max(mount.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.position.z = width < 540 ? 17 : width < 820 ? 15.5 : 13.8;
      const spread = THREE.MathUtils.clamp(width / 370, 1, 3.8);
      checkpoints.forEach((checkpoint, index) => { checkpoint.position.x = positions[index].x * spread; });
      ground.scale.x = spread;
      grid.scale.x = spread;
      updateRoute(spread);
      camera.updateProjectionMatrix();
    });
    resizeObserver.observe(mount);

    const timer = new THREE.Timer();
    timer.connect(document);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let animationId = 0;
    const render = () => {
      timer.update();
      const delta = timer.getDelta();
      const elapsed = timer.getElapsed();
      const target = positions[targetIndexRef.current] ?? positions[0];
      const spread = THREE.MathUtils.clamp(mount.clientWidth / 370, 1, 3.8);
      rover.position.x = reducedMotion ? target.x * spread : THREE.MathUtils.damp(rover.position.x, target.x * spread, 2.2, delta);
      rover.position.z = reducedMotion ? target.z : THREE.MathUtils.damp(rover.position.z, target.z, 2.2, delta);
      rover.position.y = reducedMotion ? 0.18 : 0.18 + Math.sin(elapsed * 2.4) * 0.035;
      rover.rotation.y = reducedMotion ? 0.22 : 0.22 + Math.sin(elapsed * 0.7) * 0.05;
      wheels.forEach((wheel) => { wheel.rotation.x = elapsed * 2.6; });
      rings.forEach((ring, index) => {
        const material = ring.material as THREE.MeshBasicMaterial;
        material.opacity = index === targetIndexRef.current ? 0.65 + Math.sin(elapsed * 3) * 0.2 : 0.34;
        ring.scale.setScalar(index === targetIndexRef.current ? 1 + Math.sin(elapsed * 3) * 0.045 : 1);
        const group = checkpoints[index];
        const center = group.userData.center as THREE.Mesh;
        center.scale.setScalar(index <= completedRef.current ? 1.13 : index === targetIndexRef.current ? 1 + Math.sin(elapsed * 2.7) * 0.08 : 1);
      });
      stars.rotation.y = Math.sin(elapsed * 0.08) * 0.035;
      renderer.render(scene, camera);
      if (!reducedMotion) animationId = window.requestAnimationFrame(render);
    };
    render();

    return () => {
      window.cancelAnimationFrame(animationId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Points) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      timer.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div className="rover-scene" ref={mountRef} aria-label="Interactive 3D workflow mission map" />;
}

export function WorkflowExperience({ project }: Props) {
  const [mode, setMode] = useState<"live" | "demo">("live");
  const [demoStep, setDemoStep] = useState(-1);
  const [selectedStep, setSelectedStep] = useState(0);
  const [playing, setPlaying] = useState(false);

  const liveStep = useMemo(() => {
    if (project?.status === "completed") return stages.length - 1;
    return Math.max(0, phaseStage[project?.current_phase ?? "intake"] ?? 0);
  }, [project?.current_phase, project?.status]);
  const activeStep = mode === "demo" ? Math.max(0, demoStep) : liveStep;
  const completedThrough = mode === "demo"
    ? demoStep >= stages.length - 1 ? stages.length - 1 : demoStep - 1
    : project?.status === "completed" ? stages.length - 1 : liveStep - 1;
  const selected = stages[selectedStep] ?? stages[0];
  const completedAgents = project?.completed_agents ?? [];
  const currentAgentsDone = selected.agents.filter((agent) => completedAgents.includes(agent)).length;
  const liveStageDone = project?.status === "completed" || (currentAgentsDone === selected.agents.length && selectedStep < liveStep);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setDemoStep((step) => {
        return Math.min(stages.length - 1, step + 1);
      });
    }, 2400);
    return () => window.clearInterval(timer);
  }, [playing]);

  useEffect(() => {
    if (demoStep >= 0) setSelectedStep(demoStep);
    if (demoStep >= stages.length - 1) setPlaying(false);
  }, [demoStep]);

  function openDemo() {
    setMode("demo");
    setDemoStep(-1);
    setSelectedStep(0);
    setPlaying(false);
  }

  function advanceDemo() {
    setDemoStep((step) => Math.min(stages.length - 1, step + 1));
  }

  const demoDone = mode === "demo" && demoStep >= stages.length - 1;

  return (
    <section className="workflow-experience" aria-label="Workflow mission map">
      <div className="mission-head">
        <div>
          <p className="section-title">Mission control</p>
          <h2>{mode === "demo" ? "MarketPulse: from idea to launch" : project ? "Your project, in motion" : "See how a project moves"}</h2>
          <p className="mission-subtitle">
            {mode === "demo" ? "A guided sample run through the complete software workflow." : project ? "Select a checkpoint to see its team and handoff. Live progress follows your project." : "Explore a complete sample workflow, or create a project to track your own."}
          </p>
        </div>
        <div className="mission-mode" role="group" aria-label="Workflow view">
          <button className={mode === "live" ? "selected" : ""} onClick={() => { setMode("live"); setPlaying(false); }}>My project</button>
          <button className={mode === "demo" ? "selected" : ""} onClick={openDemo}><Sparkles size={14} /> Sample demo</button>
        </div>
      </div>

      <div className="mission-world">
        <div className="world-topline">
          <span><span className={`mission-live-dot ${mode === "demo" ? "demo" : ""}`} />{mode === "demo" ? demoDone ? "DEMO COMPLETE" : demoStep < 0 ? "DEMO READY" : "GUIDED SAMPLE" : project?.status === "running" ? "LIVE PROJECT" : project?.status?.toUpperCase() ?? "MISSION MAP"}</span>
          <span>{mode === "demo" ? `${Math.max(0, demoStep + 1)} / ${stages.length} stages` : project ? `${project.completed_agents.length} / 14 employees complete` : "6 stages"}</span>
        </div>
        <RoverScene activeIndex={activeStep} completedThrough={completedThrough} onSelect={setSelectedStep} />
        <div className="stage-rail" role="tablist" aria-label="Workflow stages">
          {stages.map((stage, index) => {
            const done = mode === "demo" ? index < demoStep || demoDone : index < liveStep || Boolean(project?.status === "completed");
            const current = index === activeStep;
            return (
              <button key={stage.id} className={`stage-stop ${current ? "current" : ""} ${done ? "complete" : ""} ${selectedStep === index ? "inspected" : ""}`} onClick={() => setSelectedStep(index)} role="tab" aria-selected={selectedStep === index}>
                <span className="stage-mark">{done ? <Check size={13} /> : String(index + 1).padStart(2, "0")}</span>
                <span className="stage-stop-label">{stage.short}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="mission-bottom">
        <div className="mission-inspector" role="tabpanel">
          <div className="mission-inspector-title">
            <span className="stage-index">STAGE {String(selectedStep + 1).padStart(2, "0")}</span>
            <span className={`stage-state ${mode === "demo" ? demoDone || selectedStep < demoStep ? "done" : selectedStep === demoStep ? "active" : "waiting" : liveStageDone ? "done" : selectedStep === liveStep ? "active" : "waiting"}`}>
              {mode === "demo" ? demoDone || selectedStep < demoStep ? "Complete" : selectedStep === demoStep ? "In progress" : "Up next" : liveStageDone ? "Complete" : selectedStep === liveStep ? project?.status === "running" ? "In progress" : "Current stage" : selectedStep < liveStep ? "Complete" : "Up next"}
            </span>
          </div>
          <h3>{selected.title}</h3>
          <p className="stage-description">{mode === "demo" ? selected.demo : `${selected.agents.length} specialists share work at this stage. Select a team member in the employee board for their detailed role.`}</p>
          <div className="stage-output-row">
            {(mode === "demo" ? [demoArtifacts[selectedStep] ?? selected.outputs[0], ...selected.outputs.slice(1, 3)] : selected.outputs).map((output) => <span key={output}>{output}</span>)}
          </div>
          <div className="stage-team">TEAM <strong>{selected.agents.map((agent) => agent.replaceAll("_", " ")).join(" · ")}</strong></div>
        </div>

        {mode === "demo" ? (
          <div className="demo-console">
            <div className="demo-console-copy">
              <span className="demo-kicker">INTERACTIVE WALKTHROUGH</span>
              <strong>{demoDone ? "A full product cycle, end to end." : demoStep < 0 ? "Take a product from idea to operation." : `Checkpoint ${demoStep + 1}: ${stages[demoStep].short}`}</strong>
              <span>{demoDone ? "The sample is complete. Replay it or switch to your project." : "No API key needed. This sample does not create a project or change files."}</span>
            </div>
            <div className="demo-controls">
              <button className="icon-control" aria-label="Reset demo" title="Reset demo" onClick={openDemo}><RotateCcw size={16} /></button>
              <button className="icon-control" aria-label={playing ? "Pause demo" : "Play demo"} title={playing ? "Pause demo" : "Play demo"} disabled={demoDone} onClick={() => { if (demoStep < 0) setDemoStep(0); setPlaying((value) => !value); }}>{playing ? <Pause size={16} /> : <Play size={16} />}</button>
              <button className="demo-next" onClick={advanceDemo} disabled={demoDone}>{demoStep < 0 ? "Start sample" : demoDone ? "Complete" : "Next stage"}{!demoDone && <ArrowRight size={15} />}</button>
            </div>
          </div>
        ) : (
          <div className="live-console">
            <div>
              <span className="demo-kicker">PROJECT STATUS</span>
              <strong>{project ? `${project.status[0].toUpperCase()}${project.status.slice(1)} · ${project.current_phase.replaceAll("_", " ")}` : "No project selected"}</strong>
              <span>{project ? "The map follows pipeline updates as they arrive." : "Create a project to see its real progress here."}</span>
            </div>
            <button className="demo-next" onClick={openDemo}><Sparkles size={15} /> Explore sample</button>
          </div>
        )}
      </div>
    </section>
  );
}
