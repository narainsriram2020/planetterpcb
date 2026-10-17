import Image from "next/image";
import Link from "next/link";
import styles from "./Logo.module.css";

// shell.png is the shell artwork with a transparent background (258×325).
const SHELL_ASPECT = 258 / 325;

/** The turtle-shell mark; `size` is its height in pixels. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <Image
      src="/shell.png"
      alt=""
      aria-hidden="true"
      width={Math.round(size * SHELL_ASPECT)}
      height={size}
      priority
    />
  );
}

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className={styles.logo} aria-label="TerpAdvisor home">
      <LogoMark size={30} />
      <span className={styles.wordmark}>
        Terp<span className={styles.accent}>Advisor</span>
      </span>
    </Link>
  );
}
