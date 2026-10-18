import type { BotMessage, Card, ChatMessage, Conversation, ToolStep } from "@/types/chat";
import { API_URL, ChatRequestError, errorMessage } from "./chatStream";
import { getSupabase } from "./supabase";

// Saved chats. Reads, renames, and deletes go straight to Supabase (row-level
// security limits them to the signed-in user); only the backend writes messages.

interface MessageRow {
  id: number;
  role: "user" | "bot";
  text: string;
  steps: ToolStep[];
  cards: Card[];
  status: "done" | "error";
}

function db() {
  const supabase = getSupabase();
  if (!supabase) throw new Error("Accounts are not configured.");
  return supabase;
}

export async function listConversations(): Promise<Conversation[]> {
  const { data, error } = await db()
    .from("conversations")
    .select("id,title,updated_at")
    .order("updated_at", { ascending: false })
    .limit(100);
  if (error) throw error;
  return data ?? [];
}

export async function loadMessages(conversationId: string): Promise<ChatMessage[]> {
  const { data, error } = await db()
    .from("messages")
    .select("id,role,text,steps,cards,status")
    .eq("conversation_id", conversationId)
    .order("id", { ascending: true });
  if (error) throw error;
  return (data as MessageRow[]).map((row): ChatMessage =>
    row.role === "user"
      ? { id: String(row.id), role: "user", text: row.text }
      : ({ id: String(row.id), role: "bot", text: row.text, steps: row.steps, cards: row.cards, status: row.status } satisfies BotMessage),
  );
}

export async function renameConversation(id: string, title: string): Promise<void> {
  const { error } = await db().from("conversations").update({ title }).eq("id", id);
  if (error) throw error;
}

export async function deleteConversation(id: string): Promise<void> {
  const { error } = await db().from("conversations").delete().eq("id", id);
  if (error) throw error;
}

export async function deleteAllConversations(userId: string): Promise<void> {
  const { error } = await db().from("conversations").delete().eq("user_id", userId);
  if (error) throw error;
}

/** Deletes the account and every saved chat (done by the backend, which holds the admin key). */
export async function deleteAccount(accessToken: string): Promise<void> {
  const res = await fetch(`${API_URL}/account/delete`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new ChatRequestError(await errorMessage(res));
}
