"use client";

import { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import "./chat.css";

export default function ChatPage() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000/chat";

  const sendMessage = async () => {
    if (!prompt.trim()) return;
    setLoading(true);

    const userMsg = { role: "user", text: prompt };
    setMessages((prev) => [...prev, userMsg]);
    setPrompt("");

    try {
      const res = await fetch(BACKEND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json();
      const botMsg = {
        role: "bot",
        text: data.reply || "⚠️ No response from chatbot.",
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "❌ Error connecting to backend." },
      ]);
    } finally {
      setLoading(false);
    }
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

  const quickPrompts = [
    "What are the best CMSC electives?",
    "Who should I take for CMSC330?",
    "Show me easy GenEd options.",
    "Tell me about CMSC216 labs.",
  ];

  const messageVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1 },
  };

  const sanitizeText = (text: string) => text.replace(/\*\*/g, "").replace(/\*/g, "");

  return (
    <main className="chat-wrapper">
      <div className="chat-container">
        <header className="chat-header">
          <div className="header-content">
            <div className="status-indicator">
              <span className={`status-dot ${loading ? "active" : ""}`} />
              <span className="status-text">{loading ? "Thinking..." : "Ready"}</span>
            </div>
            <h1 className="chat-title">UMD Course Concierge</h1>
            <p className="chat-subtitle">
              Ask about courses, professors, or schedules—answers stay grounded in PlanetTerp data.
            </p>
          </div>
          
          <div className="quick-prompts">
            {quickPrompts.map((text) => (
              <button
                key={text}
                onClick={() => setPrompt(text)}
                className="prompt-chip"
                type="button"
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
                <div className="empty-icon">👋</div>
                <p className="empty-text">
                  Hey Terp! Ask about requirements, compare professors, or paste a schedule idea to get personalized guidance.
                </p>
              </motion.div>
            )}

            {messages.map((msg, i) => (
              <motion.div
                key={`${msg.role}-${i}-${msg.text.slice(0, 10)}`}
                className={`message ${msg.role}`}
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={messageVariants}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                <div className="message-avatar">{msg.role === "user" ? "👤" : "🤖"}</div>
                <div className="message-bubble">{sanitizeText(msg.text)}</div>
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
            placeholder="Ask me about CMSC132, GenEds, or professors..."
            rows={3}
            className="message-input"
          />
          <button type="submit" disabled={loading || !prompt.trim()} className="send-button">
            <span>{loading ? "Thinking..." : "Send"}</span>
          </button>
        </form>
      </div>
    </main>
  );
}