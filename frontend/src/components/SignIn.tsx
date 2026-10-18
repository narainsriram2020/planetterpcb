"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChartColumn, History, MessageSquare, X } from "lucide-react";
import { signInWithGoogle } from "@/lib/auth";
import { LogoMark } from "./Logo";
import styles from "./SignIn.module.css";

export function GoogleIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

const PERKS = [
  { icon: MessageSquare, text: "Unlimited questions about UMD courses and professors" },
  { icon: ChartColumn, text: "Grade charts and ratings behind every answer" },
  { icon: History, text: "Your chats are saved so you can pick up later" },
];

/** Google sign-in, shown as a dialog over the chat. */
export function SignIn({ notice, onClose }: { notice?: string | null; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Google or Supabase may send the user back with an error in the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const description = params.get("error_description") || hash.get("error_description");
    if (description) setError(description.replace(/\+/g, " "));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const signIn = async () => {
    setBusy(true);
    setError(null);
    const failure = await signInWithGoogle();
    if (failure) {
      setError(failure);
      setBusy(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.card}
        role="dialog"
        aria-modal="true"
        aria-labelledby="signin-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
        <LogoMark size={48} />
        <h1 id="signin-title" className={styles.title}>Keep going with TerpGuide</h1>
        <p className={styles.sub}>It&apos;s free. Sign in with Google to keep asking and save your chats.</p>

        {(notice || error) && <p className={styles.alert} role="alert">{error ?? notice}</p>}

        <button type="button" className={styles.google} onClick={signIn} disabled={busy} autoFocus>
          <GoogleIcon />
          {busy ? "Opening Google…" : "Continue with Google"}
        </button>

        <ul className={styles.perks}>
          {PERKS.map(({ icon: Icon, text }) => (
            <li key={text}>
              <span className={styles.perkIcon}><Icon size={15} /></span>
              {text}
            </li>
          ))}
        </ul>

        <p className={styles.fine}>
          Your chats are saved to your account, and you can delete them anytime. Questions are answered by Google
          Gemini, so skip personal info. See the <Link href="/privacy">privacy page</Link>.
        </p>
      </div>
    </div>
  );
}
