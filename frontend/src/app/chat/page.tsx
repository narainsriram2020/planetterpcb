"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ChatMessage, ChatResponse, ToolCall } from "@/types/chat";
import "./chat.css";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000/chat";

const quickPrompts = [
  "Who should I take for CMSC330?",
  "Easy GenEds about astronomy?",
  "How hard is CMSC216?",
  "Intro machine learning classes",
];

/** Short human-readable label for an MCP tool call, e.g. "Grades · CMSC330". */
function describeTool(call: ToolCall): string {
  const arg = (key: string) => {
    const value = call.arguments[key];
    return typeof value === "string" ? value : "";
  };
  switch (call.name) {
    case "search_courses":
      return `Searched courses · "${arg("query")}"`;
    case "search_professors":
      return `Searched professors · "${arg("query")}"`;
    case "get_course":
      return `Course · ${arg("course_id").toUpperCase()}`;
    case "get_grade_distribution":
      return `Grades · ${arg("course_id").toUpperCase()}${arg("professor") ? ` (${arg("professor")})` : ""}`;
    case "get_professor":
      return `Professor · ${arg("name")}`;
    default:
      return call.name;
  }
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through to the generic message
  }
  return `The server returned an error (HTTP ${res.status}). Try again in a moment.`;
}

export default function ChatPage() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // Capture current prompt to avoid stale-closure bugs
  const sendMessage = async (overrideText?: string) => {
    const text = (overrideText ?? prompt).trim();
    if (!text || loading) return;

    setLoading(true);
    setPrompt("");

    // Send prior turns (minus error notices) so the advisor has context
    const history = messages
      .filter((m) => !m.isError)
      .map(({ role, text }) => ({ role, text }));
    setMessages((prev) => [...prev, { role: "user", text }]);

    let botMsg: ChatMessage;
    try {
      const res = await fetch(BACKEND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text, history }),
      });
      if (res.ok) {
        const data: ChatResponse = await res.json();
        botMsg = { role: "bot", text: data.reply, tools: data.tools_used };
      } else {
        botMsg = { role: "bot", text: await readError(res), isError: true };
      }
    } catch {
      botMsg = {
        role: "bot",
        text: "Couldn't reach the TerpAdvisor server. Check your connection, or make sure the backend is running.",
        isError: true,
      };
    }
    setMessages((prev) => [...prev, botMsg]);
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const messageVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1 },
  };

  return (
    <main className="chat-wrapper">
      <div className="chat-container">
        <header className="chat-header">
          <div className="header-content">
            <div className="status-indicator">
              <span className={`status-dot ${loading ? "active" : ""}`} />
              <span className="status-text">{loading ? "Looking it up..." : "Ready"}</span>
            </div>
            <h1 className="chat-title">
              Terp<span className="chat-title-accent">Advisor</span>
            </h1>
            <p className="chat-subtitle">
              Ask about UMD courses, professors, and grades. Answers come from real PlanetTerp data.
            </p>
          </div>

          <div className="quick-prompts">
            {quickPrompts.map((text) => (
              <button
                key={text}
                onClick={() => sendMessage(text)}  // auto-send on chip click
                className="prompt-chip"
                type="button"
                disabled={loading}
              >
                {text}
              </button>
            ))}
          </div>
        </header>

        <div className="messages-container" role="log" aria-live="polite">
          <AnimatePresence initial={false}>
            {messages.length === 0 && !loading && (
              <motion.div
                key="empty"
                className="empty-state"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="empty-icon">🐢</div>
                <p className="empty-text">
                  Hey Terp! Ask who to take for a class, how hard a course is, or which GenEds have the best grades.
                </p>
              </motion.div>
            )}

            {messages.map((msg, i) => (
              <motion.div
                key={`${msg.role}-${i}`}
                className={`message ${msg.role}${msg.isError ? " error" : ""}`}
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={messageVariants}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                <div className="message-avatar">{msg.role === "user" ? "👤" : "🐢"}</div>
                <div className="message-body">
                  <div className="message-bubble">{msg.text}</div>
                  {msg.tools && msg.tools.length > 0 && (
                    <ul className="tool-trail" aria-label="Data TerpAdvisor looked up">
                      {msg.tools.map((call, j) => (
                        <li key={j} className={`tool-chip${call.ok ? "" : " failed"}`}>
                          {describeTool(call)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form
          className="input-form"
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
        >
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about CMSC132, a professor, or easy GenEds..."
            rows={3}
            maxLength={2000}
            className="message-input"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !prompt.trim()} className="send-button">
            <span>{loading ? "Thinking..." : "Send"}</span>
          </button>
        </form>
      </div>
    </main>
  );
}
