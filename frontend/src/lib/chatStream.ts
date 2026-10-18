import type { StreamEvent } from "@/types/chat";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ChatRequestError extends Error {}

/**
 * The server wants a sign-in: the session expired, or a guest used up their
 * free questions (`code === "guest_limit"`).
 */
export class AuthRequiredError extends ChatRequestError {
  constructor(message: string, readonly code?: string) {
    super(message);
  }
}

async function readError(res: Response): Promise<{ message: string; code?: string }> {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return { message: detail };
    if (typeof detail?.message === "string") return { message: detail.message, code: detail.code };
  } catch {
    // not JSON; fall through
  }
  return { message: `The server returned an error (HTTP ${res.status}). Try again in a moment.` };
}

export async function errorMessage(res: Response): Promise<string> {
  return (await readError(res)).message;
}

export interface ChatTurnRequest {
  prompt: string;
  /** Saved conversation to continue; omit to start a new one. */
  conversationId?: string | null;
  /** Only used when the app runs without accounts (local development). */
  history?: { role: "user" | "bot"; text: string }[];
  /** Supabase access token for the signed-in user. */
  accessToken?: string | null;
  /** Random per-browser id that the server counts free guest questions against. */
  guestId?: string | null;
}

/**
 * POST a chat turn to /chat/stream and invoke `onEvent` for each NDJSON event
 * (new conversation, tool steps, data cards, the answer) as it arrives.
 */
export async function streamChat(
  { prompt, conversationId, history = [], accessToken, guestId }: ChatTurnRequest,
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
        ...(!accessToken && guestId ? { "X-Guest-Id": guestId } : {}),
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
  if (res.status === 401) {
    const { message, code } = await readError(res);
    throw new AuthRequiredError(message, code);
  }
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
