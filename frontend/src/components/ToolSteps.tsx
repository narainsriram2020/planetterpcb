"use client";

import { useState } from "react";
import {
  BookOpen,
  ChartColumn,
  Check,
  ChevronDown,
  GraduationCap,
  LoaderCircle,
  Search,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import type { ToolStep } from "@/types/chat";
import styles from "./chat.module.css";

const TOOL_META: Record<string, { icon: LucideIcon; label: (args: Record<string, unknown>) => string }> = {
  search_courses: { icon: Search, label: (a) => `Searching courses for “${a.query ?? ""}”` },
  search_professors: { icon: Users, label: (a) => `Searching professors for “${a.query ?? ""}”` },
  get_course: { icon: BookOpen, label: (a) => `Reading course details for ${String(a.course_id ?? "").toUpperCase()}` },
  get_grade_distribution: {
    icon: ChartColumn,
    label: (a) =>
      `Pulling grade data for ${String(a.course_id ?? "").toUpperCase()}${a.professor ? ` (${a.professor})` : ""}`,
  },
  get_professor: { icon: GraduationCap, label: (a) => `Reading reviews for ${a.name ?? "professor"}` },
};

function StepRow({ step }: { step: ToolStep }) {
  const meta = TOOL_META[step.name];
  const Icon = meta?.icon ?? Search;
  return (
    <li className={`${styles.step} ${styles[step.status]}`}>
      <span className={styles.stepIcon}><Icon size={14} /></span>
      <span className={styles.stepLabel}>{meta ? meta.label(step.arguments) : step.name}</span>
      <span className={styles.stepStatus} aria-label={step.status}>
        {step.status === "running" && <LoaderCircle size={14} className={styles.spin} />}
        {step.status === "done" && <Check size={14} />}
        {step.status === "failed" && <X size={14} />}
      </span>
    </li>
  );
}

/** The agent's MCP tool calls: live while it works, collapsed once it has answered. */
export function ToolSteps({ steps, working }: { steps: ToolStep[]; working: boolean }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;

  if (working) {
    return (
      <ul className={styles.steps} aria-live="polite">
        {steps.map((step) => <StepRow key={step.id} step={step} />)}
      </ul>
    );
  }

  const failed = steps.filter((s) => s.status === "failed").length;
  return (
    <div className={styles.stepsCollapsed}>
      <button type="button" className={styles.stepsToggle} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <Check size={14} />
        Checked {steps.length} PlanetTerp {steps.length === 1 ? "source" : "sources"}
        {failed > 0 && <span className={styles.stepsFailed}> · {failed} failed</span>}
        <ChevronDown size={14} className={open ? styles.chevronOpen : undefined} />
      </button>
      {open && (
        <ul className={styles.steps}>
          {steps.map((step) => <StepRow key={step.id} step={step} />)}
        </ul>
      )}
    </div>
  );
}
