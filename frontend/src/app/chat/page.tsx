"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { ArrowUp, BookOpen, ChartColumn, GraduationCap, PanelLeft, Search, Square, SquarePen } from "lucide-react";
import type { BotMessage, ChatMessage, Conversation, StreamEvent } from "@/types/chat";
import { AuthRequiredError, ChatRequestError, streamChat } from "@/lib/chatStream";
import {
  deleteAccount, deleteAllConversations, deleteConversation, listConversations, loadMessages, renameConversation,
} from "@/lib/history";
import { accountsEnabled, getSupabase } from "@/lib/supabase";
import { useSession } from "@/lib/useSession";
import { Logo, LogoMark } from "@/components/Logo";
import { Message } from "@/components/Message";
import { Sidebar } from "@/components/Sidebar";
import { GoogleIcon, SignIn } from "@/components/SignIn";
import { ThemeToggle } from "@/components/ThemeToggle";
import ui from "@/components/ui.module.css";
import styles from "@/components/chat.module.css";

const SUGGESTIONS = [
  { icon: GraduationCap, title: "Pick a professor", prompt: "Who should I take for CMSC330?" },
  { icon: Search, title: "Find an easy GenEd", prompt: "Easy GenEds about astronomy?" },
  { icon: ChartColumn, title: "Gauge difficulty", prompt: "How hard is MATH141, and who grades nicest?" },
  { icon: BookOpen, title: "Explore a topic", prompt: "Intro machine learning classes for non-majors" },
];

function newId() {
  return Math.random().toString(36).slice(2, 10);
}

const GUEST_ID_KEY = "terpguide-guest-id";

/** Random id the server counts free guest questions against (kept per browser). */
function guestId(): string {
  try {
    let id = localStorage.getItem(GUEST_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(GUEST_ID_KEY, id);
    }
    return id;
  } catch {
    return crypto.randomUUID(); // storage blocked: counts per page load instead
  }
}

/** Fold one stream event into the in-progress bot message. */
function applyEvent(msg: BotMessage, event: StreamEvent): BotMessage {
  switch (event.type) {
    case "conversation":
    case "guest":
      return msg;
    case "tool_start":
      return { ...msg, steps: [...msg.steps, { id: event.id, name: event.name, arguments: event.arguments, status: "running" }] };
    case "tool_end":
      return {
        ...msg,
        steps: msg.steps.map((s) => (s.id === event.id ? { ...s, status: event.ok ? "done" : "failed" } : s)),
      };
    case "card":
      return { ...msg, cards: [...msg.cards.filter((c) => c.key !== event.card.key), event.card] };
    case "answer":
      return { ...msg, text: event.text };
    case "error":
      return { ...msg, text: event.message, status: "error" };
    case "done":
      return { ...msg, status: msg.status === "error" ? "error" : "done", processingTime: event.processing_time };
  }
}

export default function ChatPage() {
  const { session, loading } = useSession();
  // null = closed; otherwise the dialog is open, optionally with a reason to show.
  const [signInPrompt, setSignInPrompt] = useState<{ notice: string | null } | null>(null);

  // Without Supabase settings (local development) the chat runs without accounts.
  if (!accountsEnabled) {
    return <ChatApp session={null} guest={false} onSignInNeeded={() => {}} onSignedOut={() => {}} />;
  }
  if (loading) {
    return (
      <div className={styles.splash} aria-label="Loading">
        <LogoMark size={44} />
      </div>
    );
  }
  // Signed out, people chat as guests with a few free questions, then get asked to sign in.
  return (
    <>
      <ChatApp
        key={session?.user.id ?? "guest"}
        session={session}
        guest={!session}
        onSignInNeeded={(notice) => setSignInPrompt({ notice })}
        onSignedOut={(notice) => {
          getSupabase()?.auth.signOut();
          if (notice) setSignInPrompt({ notice });
        }}
      />
      {signInPrompt && !session && (
        <SignIn notice={signInPrompt.notice} onClose={() => setSignInPrompt(null)} />
      )}
    </>
  );
}

function ChatApp({
  session, guest, onSignInNeeded, onSignedOut,
}: {
  session: Session | null;
  guest: boolean;
  onSignInNeeded: (notice: string | null) => void;
  onSignedOut: (notice: string | null) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [working, setWorking] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(Boolean(session));
  const [activeId, setActiveId] = useState<string | null>(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [guestRemaining, setGuestRemaining] = useState<number | null>(null);
  const activeIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const meta = session?.user.user_metadata ?? {};
  const fullName: string | null = meta.full_name || meta.name || null;
  const firstName = fullName?.split(" ")[0] ?? null;

  const setActive = (id: string | null) => {
    activeIdRef.current = id;
    setActiveId(id);
  };

  const refreshConversations = useCallback(async () => {
    if (!session) return;
    try {
      setConversations(await listConversations());
    } catch {
      // keep whatever is showing; the next refresh will retry
    } finally {
      setConversationsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  // Auto-grow the composer up to a cap.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const updateBot = useCallback((id: string, update: (m: BotMessage) => BotMessage) => {
    setMessages((prev) => prev.map((m) => (m.id === id && m.role === "bot" ? update(m) : m)));
  }, []);

  const bumpConversation = (id: string, title?: string) => {
    setConversations((prev) => {
      const existing = prev.find((c) => c.id === id);
      const updated: Conversation = { id, title: title ?? existing?.title ?? "New chat", updated_at: new Date().toISOString() };
      return [updated, ...prev.filter((c) => c.id !== id)];
    });
  };

  const send = async (text: string) => {
    const prompt = text.trim();
    if (!prompt || working) return;
    if (guest && guestRemaining === 0) {
      onSignInNeeded("You've used your free questions. Sign in with Google to keep going, it's free.");
      return;
    }

    // Signed-in chats load history on the server; the no-accounts mode sends it along.
    const history = session
      ? []
      : messages
          .filter((m) => m.role === "user" || (m.status === "done" && m.text))
          .map((m) => ({ role: m.role, text: m.text }));
    const botId = newId();
    setMessages((prev) => [
      ...prev,
      { id: newId(), role: "user", text: prompt },
      { id: botId, role: "bot", text: "", steps: [], cards: [], status: "pending" },
    ]);
    setInput("");
    setWorking(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const accessToken = session ? (await getSupabase()!.auth.getSession()).data.session?.access_token : null;
      await streamChat(
        { prompt, conversationId: activeIdRef.current, history, accessToken, guestId: guest ? guestId() : null },
        (event) => {
          if (event.type === "guest") setGuestRemaining(event.remaining);
          if (event.type === "conversation") {
            setActive(event.id);
            bumpConversation(event.id, event.title);
          }
          updateBot(botId, (m) => applyEvent(m, event));
        },
        controller.signal,
      );
      if (activeIdRef.current) bumpConversation(activeIdRef.current);
    } catch (err) {
      if (err instanceof AuthRequiredError) {
        if (guest) {
          if (err.code === "guest_limit") setGuestRemaining(0);
          updateBot(botId, (m) => ({ ...m, text: "Sign in with Google to keep asking. It's free and saves your chats.", status: "error" }));
          onSignInNeeded(err.message);
        } else {
          onSignedOut(err.message);
        }
        return;
      }
      const message = controller.signal.aborted
        ? "Stopped."
        : err instanceof ChatRequestError
          ? err.message
          : "Something went wrong reading the answer. Try again.";
      updateBot(botId, (m) => ({ ...m, text: m.text || message, status: m.text ? "done" : "error" }));
    } finally {
      updateBot(botId, (m) => (m.status === "pending" ? { ...m, status: m.text ? "done" : "error", text: m.text || "No answer came back. Try again." } : m));
      setWorking(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  };

  const newChat = () => {
    abortRef.current?.abort();
    setActive(null);
    setMessages([]);
    setInput("");
    setDrawerOpen(false);
    inputRef.current?.focus();
  };

  const openConversation = async (id: string) => {
    setDrawerOpen(false);
    if (id === activeIdRef.current && !working) return;
    abortRef.current?.abort();
    setActive(id);
    setThreadLoading(true);
    try {
      const loaded = await loadMessages(id);
      if (activeIdRef.current === id) setMessages(loaded);
    } catch {
      if (activeIdRef.current === id) {
        setMessages([{ id: newId(), role: "bot", text: "Couldn't load this chat. Try again.", steps: [], cards: [], status: "error" }]);
      }
    } finally {
      setThreadLoading(false);
    }
  };

  const rename = async (id: string, title: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
    try {
      await renameConversation(id, title);
    } catch {
      refreshConversations();
    }
  };

  const remove = async (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeIdRef.current === id) newChat();
    try {
      await deleteConversation(id);
    } catch {
      refreshConversations();
    }
  };

  const removeAll = async () => {
    if (!session) return;
    newChat();
    setConversations([]);
    try {
      await deleteAllConversations(session.user.id);
    } catch {
      refreshConversations();
    }
  };

  const removeAccount = async () => {
    const token = (await getSupabase()?.auth.getSession())?.data.session?.access_token;
    if (!token) return onSignedOut("Your session expired. Sign in again.");
    try {
      await deleteAccount(token);
      onSignedOut("Your account and all of your chats were deleted.");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Couldn't delete your account. Try again.");
    }
  };

  const empty = messages.length === 0 && !threadLoading;
  const activeTitle = conversations.find((c) => c.id === activeId)?.title ?? null;

  return (
    <div className={styles.shell}>
      {session && (
        <Sidebar
          conversations={conversations}
          loading={conversationsLoading}
          activeId={activeId}
          user={{ name: fullName, email: session.user.email ?? null, avatarUrl: meta.avatar_url ?? meta.picture ?? null }}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          onSelect={openConversation}
          onNew={newChat}
          onRename={rename}
          onDelete={remove}
          onDeleteAll={removeAll}
          onDeleteAccount={removeAccount}
          onSignOut={() => onSignedOut(null)}
        />
      )}

      <div className={styles.app}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            {session ? (
              <>
                <button
                  type="button"
                  className={`${ui.iconButton} ${styles.menuButton}`}
                  onClick={() => setDrawerOpen(true)}
                  aria-label="Open saved chats"
                >
                  <PanelLeft size={18} />
                </button>
                <span className={styles.mobileOnly}><Logo /></span>
                {activeTitle && <span className={styles.chatTitle}>{activeTitle}</span>}
              </>
            ) : (
              <Logo />
            )}
          </div>
          <div className={styles.topbarActions}>
            {guest && (
              <button type="button" className={ui.button} onClick={() => onSignInNeeded(null)}>
                <GoogleIcon size={15} /> Sign in
              </button>
            )}
            {(session || messages.length > 0) && (
              <button type="button" className={`${ui.button} ${session ? styles.mobileOnly : ""}`} onClick={newChat}>
                <SquarePen size={15} /> New chat
              </button>
            )}
            <ThemeToggle />
          </div>
        </header>

        <main className={styles.main}>
          {threadLoading ? (
            <div className={styles.threadSkeleton} aria-label="Loading chat">
              <span /><span /><span />
            </div>
          ) : empty ? (
            <section className={styles.welcome}>
              <span className={styles.welcomeBadge}>
                {firstName ? `Hey ${firstName}` : "Grounded in PlanetTerp data"}
              </span>
              <h1 className={styles.welcomeTitle}>
                What are you thinking of <span className={styles.welcomeAccent}>taking</span>?
              </h1>
              <p className={styles.welcomeSub}>
                Ask about any UMD course or professor. TerpGuide pulls real grade distributions, ratings,
                and reviews, then gives you a straight answer.
              </p>
              <div className={styles.suggestions}>
                {SUGGESTIONS.map(({ icon: Icon, title, prompt }) => (
                  <button key={title} type="button" className={styles.suggestion} onClick={() => send(prompt)}>
                    <span className={styles.suggestionIcon}><Icon size={16} /></span>
                    <span className={styles.suggestionTitle}>{title}</span>
                    <span className={styles.suggestionPrompt}>{prompt}</span>
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <div className={styles.thread} role="log" aria-live="polite">
              {messages.map((m) => <Message key={m.id} message={m} />)}
              <div ref={endRef} />
            </div>
          )}
        </main>

        <footer className={styles.composerDock}>
          <form
            className={styles.composer}
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder="Ask about a course, a professor, or GenEds…"
              rows={1}
              maxLength={2000}
              aria-label="Message TerpGuide"
              autoFocus
            />
            {working ? (
              <button type="button" className={styles.sendButton} onClick={() => abortRef.current?.abort()} aria-label="Stop">
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button type="submit" className={styles.sendButton} disabled={!input.trim()} aria-label="Send">
                <ArrowUp size={18} />
              </button>
            )}
          </form>
          {guest && (
            <p className={styles.guestNote}>
              {guestRemaining === null
                ? "Try it free, no sign-in needed. "
                : guestRemaining === 0
                  ? "That was your last free question. "
                  : `${guestRemaining} free question${guestRemaining === 1 ? "" : "s"} left. `}
              <button type="button" onClick={() => onSignInNeeded(null)}>Sign in</button> to keep going and save your chats.
            </p>
          )}
          <p className={styles.disclaimer}>
            Data from PlanetTerp. Not affiliated with the University of Maryland. Questions are answered by Google Gemini, so skip personal info, and double-check before you register.
          </p>
        </footer>
      </div>
    </div>
  );
}
