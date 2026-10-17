"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import styles from "./McpConnect.module.css";

interface Client {
  id: string;
  label: string;
  where: string;
  snippet: (url: string) => string;
}

const CLIENTS: Client[] = [
  {
    id: "cursor",
    label: "Cursor",
    where: "~/.cursor/mcp.json",
    snippet: (url) => `{
  "mcpServers": {
    "terpguide": {
      "url": "${url}"
    }
  }
}`,
  },
  {
    id: "claude-code",
    label: "Claude Code",
    where: "Terminal",
    snippet: (url) => `claude mcp add --transport http terpguide ${url}`,
  },
  {
    id: "vscode",
    label: "VS Code",
    where: ".vscode/mcp.json",
    snippet: (url) => `{
  "servers": {
    "terpguide": {
      "type": "http",
      "url": "${url}"
    }
  }
}`,
  },
  {
    id: "claude",
    label: "Claude app",
    where: "Settings → Connectors → Add custom connector",
    snippet: (url) => `Name:  TerpGuide
URL:   ${url}`,
  },
];

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard blocked (insecure context or permissions); the text is still selectable.
    }
  };
  return (
    <button type="button" className={styles.copy} onClick={copy} aria-label={copied ? "Copied" : label}>
      {copied ? <Check size={14} /> : <Copy size={14} />}
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

/** The live MCP endpoint plus copy-paste setup for common MCP clients. */
export function McpConnect({ url }: { url: string }) {
  const [active, setActive] = useState(CLIENTS[0].id);
  const client = CLIENTS.find((c) => c.id === active) ?? CLIENTS[0];
  const snippet = client.snippet(url);

  return (
    <div className={styles.panel}>
      <div className={styles.endpoint}>
        <span className={styles.endpointLabel}>
          <span className={styles.liveDot} /> Live endpoint · streamable HTTP
        </span>
        <div className={styles.endpointRow}>
          <code className={styles.url}>{url}</code>
          <CopyButton text={url} label="Copy MCP server URL" />
        </div>
      </div>

      <div className={styles.tabs} role="tablist" aria-label="MCP client">
        {CLIENTS.map((c) => (
          <button
            key={c.id}
            type="button"
            role="tab"
            aria-selected={c.id === active}
            className={c.id === active ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => setActive(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className={styles.code} role="tabpanel">
        <div className={styles.codeHeader}>
          <span>{client.where}</span>
          <CopyButton text={snippet} label={`Copy ${client.label} setup`} />
        </div>
        <pre><code>{snippet}</code></pre>
      </div>
      <p className={styles.note}>No API key or install needed. Ask your AI, “who should I take for CMSC330?”</p>
    </div>
  );
}
