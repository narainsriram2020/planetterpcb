import type { StreamEvent } from "@/types/chat";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ChatRequestError extends Error {}

/** The server rejected the sign-in (missing or expired session). */
export class AuthRequiredError extends ChatRequestError {}

export async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // not JSON; fall through
  }
  return `The server returned an error (HTTP ${res.status}). Try again in a moment.`;
}

export interface ChatTurnRequest {
  prompt: string;
  /** Saved conversation to continue; omit to start a new one. */
  conversationId?: string | null;
  /** Only used when the app runs without accounts (local development). */
  history?: { role: "user" | "bot"; text: string }[];
  /** Supabase access token for the signed-in user. */
  accessToken?: string | null;
}

/**
 * POST a chat turn to /chat/stream and invoke `onEvent` for each NDJSON event
 * (new conversation, tool steps, data cards, the answer) as it arrives.
 */
export async function streamChat(
  { prompt, conversationId, history = [], accessToken }: ChatTurnRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify({ prompt, conversation_id: conversationId ?? null, history }),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ChatRequestError(
      "Couldn't reach the TerpGuide server. Check your connection, or make sure the backend is running.",
    );
  }
  if (res.status === 401) throw new AuthRequiredError(await errorMessage(res));
  if (!res.ok || !res.body) throw new ChatRequestError(await errorMessage(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let newline: number;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) onEvent(JSON.parse(line) as StreamEvent);
    }
    if (done) break;
  }
}
