"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, BookOpen, ChartColumn, GraduationCap, Search, Square, SquarePen } from "lucide-react";
import type { BotMessage, ChatMessage, StreamEvent } from "@/types/chat";
import { ChatRequestError, streamChat } from "@/lib/chatStream";
import { Logo } from "@/components/Logo";
import { Message } from "@/components/Message";
import { ThemeToggle } from "@/components/ThemeToggle";
import ui from "@/components/ui.module.css";
import styles from "@/components/chat.module.css";

const STORAGE_KEY = "terpguide-chat";

const SUGGESTIONS = [
  { icon: GraduationCap, title: "Pick a professor", prompt: "Who should I take for CMSC330?" },
  { icon: Search, title: "Find an easy GenEd", prompt: "Easy GenEds about astronomy?" },
  { icon: ChartColumn, title: "Gauge difficulty", prompt: "How hard is MATH141, and who grades nicest?" },
  { icon: BookOpen, title: "Explore a topic", prompt: "Intro machine learning classes for non-majors" },
];

function newId() {
  return Math.random().toString(36).slice(2, 10);
}

/** Fold one stream event into the in-progress bot message. */
function applyEvent(msg: BotMessage, event: StreamEvent): BotMessage {
  switch (event.type) {
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [working, setWorking] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  // Restore the last conversation (per browser) and keep it saved.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const restored: ChatMessage[] = JSON.parse(saved);
        // An answer that was still streaming when the page closed can't resume.
        setMessages(restored.map((m) =>
          m.role === "bot" && m.status === "pending" ? { ...m, status: "error", text: m.text || "Interrupted." } : m,
        ));
      }
    } catch {
      // corrupted or unavailable storage: start fresh
    }
  }, []);

  useEffect(() => {
    if (working) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch {
      // storage full or unavailable; the chat still works
    }
  }, [messages, working]);

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

  const send = async (text: string) => {
    const prompt = text.trim();
    if (!prompt || working) return;

    const history = messages
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
      await streamChat(prompt, history, (event) => updateBot(botId, (m) => applyEvent(m, event)), controller.signal);
    } catch (err) {
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
    setMessages([]);
    setInput("");
    inputRef.current?.focus();
  };

  const empty = messages.length === 0;

  return (
    <div className={styles.app}>
      <header className={styles.topbar}>
        <Logo />
        <div className={styles.topbarActions}>
          {!empty && (
            <button type="button" className={ui.button} onClick={newChat}>
              <SquarePen size={15} /> New chat
            </button>
          )}
          <ThemeToggle />
        </div>
      </header>

      <main className={styles.main}>
        {empty ? (
          <section className={styles.welcome}>
            <span className={styles.welcomeBadge}>Grounded in PlanetTerp data</span>
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
        <p className={styles.disclaimer}>
          Data from PlanetTerp. Not affiliated with the University of Maryland. Questions are answered by Google Gemini, so skip personal info, and double-check before you register.
        </p>
      </footer>
    </div>
  );
}
