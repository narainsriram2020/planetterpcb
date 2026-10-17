import type { Card } from "@/types/chat";
import { GradesCard } from "./GradesCard";
import { CourseCard, CourseList, ProfessorCard, ProfessorList } from "./InfoCards";
import styles from "./cards.module.css";

const DETAIL_KINDS = new Set(["grades", "professor", "course"]);
const ORDER = ["grades", "course", "professor", "course_list", "professor_list"];

/**
 * Detail cards (grades, courses, professors) take priority; raw search
 * results are only shown when the agent didn't drill into anything.
 */
export function CardGrid({ cards }: { cards: Card[] }) {
  const hasDetail = cards.some((c) => DETAIL_KINDS.has(c.kind));
  const visible = cards
    .filter((c) => !hasDetail || DETAIL_KINDS.has(c.kind))
    .sort((a, b) => ORDER.indexOf(a.kind) - ORDER.indexOf(b.kind))
    .slice(0, hasDetail ? 6 : 2);
  if (visible.length === 0) return null;

  return (
    <div className={styles.grid}>
      {visible.map((card) => {
        switch (card.kind) {
          case "grades":
            return <GradesCard key={card.key} card={card} />;
          case "professor":
            return <ProfessorCard key={card.key} card={card} />;
          case "course":
            return <CourseCard key={card.key} card={card} />;
          case "course_list":
            return <CourseList key={card.key} card={card} />;
          case "professor_list":
            return <ProfessorList key={card.key} card={card} />;
        }
      })}
    </div>
  );
}
