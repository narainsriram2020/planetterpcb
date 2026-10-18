import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import styles from "./privacy.module.css";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What TerpGuide stores, who can see it, and how to delete it.",
  alternates: { canonical: "/privacy" },
};

const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

export default function PrivacyPage() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Logo />
        <ThemeToggle />
      </nav>

      <main className={styles.content}>
        <Link href="/chat" className={styles.back}>
          <ArrowLeft size={15} /> Back to chat
        </Link>
        <h1>Privacy</h1>
        <p className={styles.updated}>Last updated October 17, 2026</p>

        <p>
          TerpGuide is a student project that answers questions about University of Maryland courses using public
          PlanetTerp data. Here&apos;s exactly what it keeps.
        </p>

        <h2>What&apos;s stored</h2>
        <ul>
          <li>
            <strong>Your Google sign-in basics</strong>: name, email, and profile picture, so you can sign in and see
            your own chats.
          </li>
          <li>
            <strong>Your chats</strong>: the questions you ask and TerpGuide&apos;s answers, saved to your account so you
            can come back to them.
          </li>
          <li>
            <strong>Anonymous usage stats</strong>: page views, device type, and country, through Vercel Web
            Analytics. No cookies and nothing tied to your account.
          </li>
        </ul>

        <h2>Who can see it</h2>
        <ul>
          <li>You can see your own chats. Other users can&apos;t.</li>
          <li>
            The site owner can review saved chats to find wrong answers and improve TerpGuide. Chats are never sold or
            used for ads.
          </li>
          <li>
            Questions are answered by Google Gemini, which may use them to improve Google&apos;s products. Don&apos;t
            include personal information in your questions.
          </li>
        </ul>

        <h2>Services involved</h2>
        <ul>
          <li><strong>Supabase</strong> stores accounts and chats.</li>
          <li><strong>Google Gemini</strong> writes the answers.</li>
          <li><strong>Vercel</strong> hosts the website and its analytics; <strong>Render</strong> hosts the server.</li>
          <li><strong>PlanetTerp</strong> provides the course, grade, and review data.</li>
        </ul>

        <h2>Deleting your data</h2>
        <p>
          On the chat page, open the menu under your name at the bottom of the sidebar. You can delete a single chat,
          all of your chats, or your whole account. Deleting your account removes it and every saved chat right away.
        </p>

        <h2>The fine print</h2>
        <p>
          TerpGuide is not affiliated with or endorsed by the University of Maryland or PlanetTerp. Answers can be
          wrong, so double-check before you register.
          {CONTACT_EMAIL && (
            <>
              {" "}Questions? Email <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
            </>
          )}
        </p>
      </main>
    </div>
  );
}
