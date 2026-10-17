import Link from "next/link";
import { ArrowRight, Check, ChartColumn, Database, MessageSquare, Network } from "lucide-react";
import type { GradesCard as GradesCardData } from "@/types/chat";
import { GradesCard } from "@/components/cards/GradesCard";
import { Logo, LogoMark } from "@/components/Logo";
import { Markdown } from "@/components/Markdown";
import { McpConnect } from "@/components/McpConnect";
import { ThemeToggle } from "@/components/ThemeToggle";
import ui from "@/components/ui.module.css";
import styles from "./landing.module.css";

// A real answer's data, captured from the live API (MATH141, Fall 2022 – Spring 2026).
const EXAMPLE_GRADES: GradesCardData = {
  kind: "grades",
  key: "grades:MATH141",
  course_id: "MATH141",
  semesters: "202208-202601",
  average_gpa: 2.82,
  students: 5595,
  distribution: [
    { grade: "A", count: 1796 },
    { grade: "B", count: 1949 },
    { grade: "C", count: 1231 },
    { grade: "D", count: 352 },
    { grade: "F", count: 267 },
    { grade: "W", count: 385 },
  ],
  professors: [
    { name: "Jonathan Fernandes", gpa: 3.26, students: 316, last_taught: "202508" },
    { name: "Matthew Wilson", gpa: 3.09, students: 119, last_taught: "202601" },
    { name: "Shin Song", gpa: 3.06, students: 315, last_taught: "202601" },
    { name: "Steven Chadwick", gpa: 2.84, students: 722, last_taught: "202601" },
    { name: "James Conway", gpa: 2.82, students: 481, last_taught: "202601" },
    { name: "Kendall Williams", gpa: 2.49, students: 224, last_taught: "202508" },
  ],
};

const EXAMPLE_ANSWER =
  "**MATH141** averages a 2.82, so section choice matters. Recently, **Jonathan Fernandes** (3.26 across 316 students), " +
  "**Matthew Wilson** (3.09) and **Shin Song** (3.06) have had the friendliest grade distributions.";

const TOOLS = [
  { name: "search_courses", detail: "Semantic search over 25k+ courses" },
  { name: "search_professors", detail: "Find professors by name or by what students say" },
  { name: "get_course", detail: "Description, credits, GenEds, average GPA" },
  { name: "get_grade_distribution", detail: "Grades by semester and professor" },
  { name: "get_professor", detail: "Rating and the latest reviews" },
];

// The deployed API serves the MCP server at /mcp/ (trailing slash avoids a redirect).
const MCP_URL = `${(process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "")}/mcp/`;

export default function LandingPage() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Logo />
        <div className={styles.navActions}>
          <a className={styles.navLink} href="#how">How it works</a>
          <a className={styles.navLink} href="#mcp">MCP server</a>
          <ThemeToggle />
          <Link href="/chat" className={ui.buttonPrimary}>
            Open app <ArrowRight size={15} />
          </Link>
        </div>
      </nav>

      <header className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.badge}>AI course advisor for UMD</span>
          <h1 className={styles.heroTitle}>
            Pick classes with real data, <span className={styles.accent}>not vibes.</span>
          </h1>
          <p className={styles.heroSub}>
            Ask who to take, how hard a class is, or which GenEds grade nicest. TerpGuide pulls PlanetTerp grade
            distributions, ratings, and reviews, and shows you the numbers behind every answer.
          </p>
          <div className={styles.heroCtas}>
            <Link href="/chat" className={`${ui.buttonPrimary} ${styles.bigButton}`}>
              Start asking <ArrowRight size={17} />
            </Link>
            <a href="#how" className={`${ui.button} ${styles.bigButton}`}>See how it works</a>
          </div>
          <ul className={styles.stats}>
            <li><strong>25k+</strong> courses</li>
            <li><strong>14k+</strong> professors</li>
            <li><strong>5</strong> MCP tools</li>
          </ul>
        </div>

        <div className={styles.preview} aria-label="Example answer">
          <div className={styles.previewBar}>
            <span /><span /><span />
            <em>Example · real PlanetTerp data</em>
          </div>
          <div className={styles.previewBody}>
            <div className={styles.previewUser}>Who should I take for MATH141?</div>
            <div className={styles.previewBot}>
              <span className={styles.previewAvatar}><LogoMark size={20} /></span>
              <div className={styles.previewContent}>
                <span className={styles.previewSteps}>
                  <Check size={13} /> Checked grade data for MATH141
                </span>
                <Markdown text={EXAMPLE_ANSWER} />
              </div>
            </div>
            <div className={styles.previewCard}>
              <GradesCard card={EXAMPLE_GRADES} />
            </div>
          </div>
        </div>
      </header>

      <section id="how" className={styles.section}>
        <h2 className={styles.sectionTitle}>How it works</h2>
        <div className={styles.steps}>
          <article className={styles.stepCard}>
            <span className={styles.stepIcon}><MessageSquare size={18} /></span>
            <h3>Ask like you&apos;d ask a friend</h3>
            <p>“Is CMSC216 brutal?” “Chill DSHS GenEd?” Follow-ups keep the context of your conversation.</p>
          </article>
          <article className={styles.stepCard}>
            <span className={styles.stepIcon}><Network size={18} /></span>
            <h3>An agent picks the lookups</h3>
            <p>Gemini decides which PlanetTerp tools to call through an MCP server, in parallel when it can, and you watch each step happen.</p>
          </article>
          <article className={styles.stepCard}>
            <span className={styles.stepIcon}><ChartColumn size={18} /></span>
            <h3>Answers you can check</h3>
            <p>A short recommendation, with the grade charts, ratings, and reviews it was based on right underneath.</p>
          </article>
        </div>
      </section>

      <section id="mcp" className={`${styles.section} ${styles.split}`}>
        <div>
          <span className={styles.eyebrow}><Database size={14} /> Under the hood</span>
          <h2 className={styles.sectionTitle}>A real MCP server you can plug into any AI client</h2>
          <p className={styles.sectionSub}>
            The same five tools TerpGuide uses are a public Model Context Protocol server. Add it to Cursor,
            Claude, or VS Code and your own AI assistant can look up UMD courses, grades, and professors.
          </p>
          <ul className={styles.toolList}>
            {TOOLS.map((t) => (
              <li key={t.name}>
                <span className={ui.code}>{t.name}</span>
                <span>{t.detail}</span>
              </li>
            ))}
          </ul>
        </div>
        <McpConnect url={MCP_URL} />
      </section>

      <section className={styles.finalCta}>
        <h2>Registration&apos;s coming. Plan with data.</h2>
        <Link href="/chat" className={`${ui.buttonPrimary} ${styles.bigButton}`}>
          Open TerpGuide <ArrowRight size={17} />
        </Link>
      </section>

      <footer className={styles.footer}>
        <span>Data from <a href="https://planetterp.com" target="_blank" rel="noreferrer">PlanetTerp</a>.</span>
        <span>Not affiliated with or endorsed by the University of Maryland.</span>
      </footer>
    </div>
  );
}
