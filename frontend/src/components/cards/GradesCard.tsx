"use client";

import { useState } from "react";
import type { GradesCard as GradesCardData } from "@/types/chat";
import { formatCount, formatGpa, formatSemester, formatSemesterRange } from "@/lib/format";
import styles from "./cards.module.css";

const GPA_MAX = 4;

interface Tip {
  x: number;
  y: number;
  value: string;
  label: string;
}

function Tooltip({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  return (
    <div className={styles.tooltip} style={{ left: tip.x, top: tip.y }} role="status">
      <strong>{tip.value}</strong>
      <span>{tip.label}</span>
    </div>
  );
}

const TIP_HALF_WIDTH = 90;

function tipFor(target: HTMLElement, value: string, label: string): Tip {
  const box = target.getBoundingClientRect();
  const parent = target.closest(`.${styles.chartArea}`)!.getBoundingClientRect();
  const center = box.left - parent.left + box.width / 2;
  // Keep the tooltip inside the chart instead of spilling past the card edge.
  const x = Math.min(Math.max(center, TIP_HALF_WIDTH), Math.max(parent.width - TIP_HALF_WIDTH, TIP_HALF_WIDTH));
  return { x, y: box.top - parent.top, value, label };
}

function Distribution({ card }: { card: GradesCardData }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const total = card.distribution.reduce((sum, d) => sum + d.count, 0) || 1;
  const max = Math.max(...card.distribution.map((d) => d.count), 1);
  const peak = card.distribution.findIndex((d) => d.count === max);

  return (
    <div className={styles.chartArea} onMouseLeave={() => setTip(null)}>
      <div className={styles.columns} role="list" aria-label="Grade distribution">
        {card.distribution.map((d, i) => {
          const pct = Math.round((d.count / total) * 100);
          const show = (el: HTMLElement) =>
            setTip(tipFor(el, `${pct}%`, `${d.grade === "W" ? "Withdrew" : d.grade + " grades"} · ${formatCount(d.count)} students`));
          return (
            <div key={d.grade} className={styles.column} role="listitem">
              <div className={styles.columnTrack}>
                <div
                  className={styles.columnBar}
                  // tallest bar fills 85% so its cap label has headroom
                  style={{ height: `${Math.max((d.count / max) * 85, 1.5)}%` }}
                  tabIndex={0}
                  aria-label={`${d.grade}: ${pct}% (${d.count} students)`}
                  onMouseEnter={(e) => show(e.currentTarget)}
                  onFocus={(e) => show(e.currentTarget)}
                  onBlur={() => setTip(null)}
                >
                  {i === peak && <span className={styles.capLabel}>{pct}%</span>}
                </div>
              </div>
              <span className={styles.columnLabel}>{d.grade}</span>
            </div>
          );
        })}
      </div>
      <Tooltip tip={tip} />
    </div>
  );
}

function ProfessorBars({ card }: { card: GradesCardData }) {
  const [tip, setTip] = useState<Tip | null>(null);
  return (
    <div className={styles.chartArea} onMouseLeave={() => setTip(null)}>
      <ul className={styles.hbars} aria-label="Average GPA by professor">
        {card.professors.map((p) => {
          const show = (el: HTMLElement) =>
            setTip(tipFor(el, `${formatGpa(p.gpa)} GPA`, `${formatCount(p.students)} students · last taught ${formatSemester(p.last_taught)}`));
          return (
            <li key={p.name} className={styles.hbarRow}>
              <span className={styles.hbarName} title={p.name}>{p.name}</span>
              <div className={styles.hbarTrack}>
                <div
                  className={styles.hbar}
                  // leave room for the value label at the bar's tip
                  style={{ width: `calc((100% - 44px) * ${Math.min(p.gpa / GPA_MAX, 1)})` }}
                  tabIndex={0}
                  aria-label={`${p.name}: ${formatGpa(p.gpa)} average GPA, ${p.students} students`}
                  onMouseEnter={(e) => show(e.currentTarget)}
                  onFocus={(e) => show(e.currentTarget)}
                  onBlur={() => setTip(null)}
                />
                <span className={styles.hbarValue}>{formatGpa(p.gpa)}</span>
              </div>
            </li>
          );
        })}
      </ul>
      <Tooltip tip={tip} />
    </div>
  );
}

export function GradesCard({ card }: { card: GradesCardData }) {
  const total = card.distribution.reduce((sum, d) => sum + d.count, 0) || 1;
  return (
    <article className={`${styles.card} ${styles.wide}`}>
      <header className={styles.cardHeader}>
        <div>
          <span className={styles.eyebrow}>Grade distribution</span>
          <h3 className={styles.cardTitle}>{card.course_id}</h3>
        </div>
        <div className={styles.stat}>
          <span className={styles.statValue}>{formatGpa(card.average_gpa)}</span>
          <span className={styles.statLabel}>recent GPA</span>
        </div>
      </header>
      <p className={styles.meta}>
        {formatSemesterRange(card.semesters)} · {formatCount(card.students)} graded students
      </p>

      <div className={styles.gradeGrid}>
        <section>
          <h4 className={styles.chartTitle}>Share of grades</h4>
          <Distribution card={card} />
        </section>
        {card.professors.length > 0 && (
          <section>
            <h4 className={styles.chartTitle}>Average GPA by recent professor</h4>
            <ProfessorBars card={card} />
          </section>
        )}
      </div>

      <details className={styles.tableToggle}>
        <summary>View as table</summary>
        <div className={styles.tables}>
          <table>
            <thead>
              <tr><th>Grade</th><th>Students</th><th>Share</th></tr>
            </thead>
            <tbody>
              {card.distribution.map((d) => (
                <tr key={d.grade}>
                  <td>{d.grade}</td>
                  <td>{formatCount(d.count)}</td>
                  <td>{Math.round((d.count / total) * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {card.professors.length > 0 && (
            <table>
              <thead>
                <tr><th>Professor</th><th>GPA</th><th>Students</th><th>Last taught</th></tr>
              </thead>
              <tbody>
                {card.professors.map((p) => (
                  <tr key={p.name}>
                    <td>{p.name}</td>
                    <td>{formatGpa(p.gpa)}</td>
                    <td>{formatCount(p.students)}</td>
                    <td>{formatSemester(p.last_taught)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </details>
    </article>
  );
}
