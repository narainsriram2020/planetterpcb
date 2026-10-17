export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  ok: boolean;
}

export interface ChatMessage {
  role: "user" | "bot";
  text: string;
  tools?: ToolCall[];
  isError?: boolean;
}

/** Response from the backend's POST /chat. */
export interface ChatResponse {
  reply: string;
  tools_used: ToolCall[];
  processing_time: string;
}
