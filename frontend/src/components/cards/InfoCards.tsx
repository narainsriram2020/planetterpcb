import { ArrowUpRight, Star } from "lucide-react";
import type {
  CourseCard as CourseCardData,
  CourseListCard,
  ProfessorCard as ProfessorCardData,
  ProfessorListCard,
} from "@/types/chat";
import { formatCount, formatGpa } from "@/lib/format";
import ui from "../ui.module.css";
import styles from "./cards.module.css";

const MAX_COURSE_CHIPS = 6;

const STAR_SIZE = 16;

/** Five stars, each filled by its own share of the rating (3.15 → 3 full, 15% of the 4th). */
function Stars({ rating }: { rating: number }) {
  const clamped = Math.max(0, Math.min(rating, 5));
  return (
    <span className={styles.stars} role="img" aria-label={`Rated ${rating.toFixed(2)} out of 5`}>
      {[0, 1, 2, 3, 4].map((i) => {
        const fill = Math.max(0, Math.min(clamped - i, 1));
        return (
          <span key={i} className={styles.star}>
            <Star size={STAR_SIZE} fill="currentColor" strokeWidth={1.5} className={styles.starEmpty} />
            {fill > 0 && (
              // Fixed-size star clipped by its wrapper, so partial fills never shrink the icon.
              <span className={styles.starFill} style={{ width: `${fill * 100}%` }}>
                <Star size={STAR_SIZE} fill="currentColor" strokeWidth={1.5} />
              </span>
            )}
          </span>
        );
      })}
    </span>
  );
}

function ExternalLink({ href, label }: { href: string | null; label: string }) {
  if (!href) return null;
  return (
    <a className={styles.link} href={href} target="_blank" rel="noreferrer">
      {label} <ArrowUpRight size={14} />
    </a>
  );
}

export function ProfessorCard({ card }: { card: ProfessorCardData }) {
  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        <div>
          <span className={styles.eyebrow}>Professor</span>
          <h3 className={styles.cardTitle}>{card.name}</h3>
        </div>
        {typeof card.rating === "number" && (
          <div className={styles.stat}>
            <span className={styles.statValue}>{card.rating.toFixed(2)}</span>
            <span className={styles.statLabel}>of 5</span>
          </div>
        )}
      </header>
      {typeof card.rating === "number" && (
        <p className={styles.ratingRow}>
          <Stars rating={card.rating} />
          <span className={styles.meta}>{formatCount(card.review_count)} reviews</span>
        </p>
      )}
      {card.courses.length > 0 && (
        <div className={styles.chips}>
          {card.courses.slice(0, MAX_COURSE_CHIPS).map((c) => <span key={c} className={ui.code}>{c}</span>)}
          {card.courses.length > MAX_COURSE_CHIPS && (
            <span className={styles.moreChip}>+{card.courses.length - MAX_COURSE_CHIPS}</span>
          )}
        </div>
      )}
      {card.review && (
        // Raw student reviews can be harsh; keep them one click away instead of front and center.
        <details className={styles.reviewToggle}>
          <summary>
            Latest review
            {card.review.rating != null && <span className={styles.meta}> · {card.review.rating}/5</span>}
          </summary>
          <blockquote className={styles.quote}>
            <p>“{card.review.text}”</p>
            <footer>{[card.review.course, card.review.date].filter(Boolean).join(" · ")}</footer>
          </blockquote>
        </details>
      )}
      <ExternalLink href={card.url} label="All reviews on PlanetTerp" />
    </article>
  );
}

export function CourseCard({ card }: { card: CourseCardData }) {
  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        <div>
          <span className={styles.eyebrow}>
            Course{card.credits ? ` · ${card.credits} credits` : ""}
          </span>
          <h3 className={styles.cardTitle}>{card.course_id}</h3>
        </div>
        <div className={styles.stat}>
          <span className={styles.statValue}>{formatGpa(card.average_gpa)}</span>
          <span className={styles.statLabel}>all-time GPA</span>
        </div>
      </header>
      {card.title && <p className={styles.courseTitle}>{card.title}</p>}
      {card.geneds.length > 0 && (
        <div className={styles.chips}>
          {card.geneds.map((g) => <span key={g} className={styles.genedChip}>{g}</span>)}
        </div>
      )}
      {card.description && <p className={styles.description}>{card.description}</p>}
      <ExternalLink href={card.url} label="View on PlanetTerp" />
    </article>
  );
}

export function CourseList({ card }: { card: CourseListCard }) {
  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        <div>
          <span className={styles.eyebrow}>Search results</span>
          <h3 className={styles.cardTitleSmall}>“{card.query}”</h3>
        </div>
      </header>
      <ul className={styles.list}>
        {card.results.map((r) => (
          <li key={r.course_id}>
            <span className={ui.code}>{r.course_id}</span>
            <span className={styles.listTitle}>{r.title ?? "Untitled"}</span>
            <span className={styles.listValue}>{formatGpa(r.average_gpa)}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function ProfessorList({ card }: { card: ProfessorListCard }) {
  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        <div>
          <span className={styles.eyebrow}>Professors</span>
          <h3 className={styles.cardTitleSmall}>“{card.query}”</h3>
        </div>
      </header>
      <ul className={styles.list}>
        {card.results.map((r) => (
          <li key={r.name}>
            <span className={styles.listTitle}>{r.name}</span>
            <span className={styles.listValue}>
              {typeof r.rating === "number" ? `${r.rating.toFixed(2)} ★` : "—"}
            </span>
          </li>
        ))}
      </ul>
    </article>
  );
}
