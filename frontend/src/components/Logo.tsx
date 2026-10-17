import Link from "next/link";
import styles from "./Logo.module.css";

/** Turtle-shell mark: a red hexagon with a gold center scute. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 2.5 27.7 9.25v13.5L16 29.5 4.3 22.75V9.25z" fill="var(--red)" />
      <path d="M16 9.6 21.5 12.8v6.4L16 22.4l-5.5-3.2v-6.4z" fill="var(--gold)" />
      <path
        d="M16 2.5v7.1M27.7 9.25l-6.2 3.55M27.7 22.75l-6.2-3.55M16 29.5v-7.1M4.3 22.75l6.2-3.55M4.3 9.25l6.2 3.55"
        stroke="var(--gold)"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className={styles.logo} aria-label="TerpAdvisor home">
      <LogoMark />
      <span className={styles.wordmark}>
        Terp<span className={styles.accent}>Advisor</span>
      </span>
    </Link>
  );
}
