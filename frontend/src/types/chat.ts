// Mirrors the cards built in backend/app/cards.py.

export interface GradesCard {
  kind: "grades";
  key: string;
  course_id: string;
  semesters: string | null;
  average_gpa: number | null;
  students: number | null;
  distribution: { grade: string; count: number }[];
  professors: { name: string; gpa: number; students: number; last_taught: string }[];
}

export interface ProfessorCard {
  kind: "professor";
  key: string;
  name: string;
  rating: number | null;
  review_count: number | null;
  courses: string[];
  review: { course: string | null; rating: number | null; date: string | null; text: string } | null;
  url: string | null;
}

export interface CourseCard {
  kind: "course";
  key: string;
  course_id: string;
  title: string | null;
  credits: string | null;
  average_gpa: number | null;
  geneds: string[];
  professor_count: number | null;
  description: string;
  url: string | null;
}

export interface CourseListCard {
  kind: "course_list";
  key: string;
  query: string;
  results: { course_id: string; title: string | null; average_gpa: number | null }[];
}

export interface ProfessorListCard {
  kind: "professor_list";
  key: string;
  query: string;
  results: { name: string; rating: number | null; review_count: number | null }[];
}

export type Card = GradesCard | ProfessorCard | CourseCard | CourseListCard | ProfessorListCard;

export interface ToolStep {
  id: number;
  name: string;
  arguments: Record<string, unknown>;
  status: "running" | "done" | "failed";
}

export type StreamEvent =
  | { type: "conversation"; id: string; title: string }
  | { type: "tool_start"; id: number; name: string; arguments: Record<string, unknown> }
  | { type: "tool_end"; id: number; name: string; ok: boolean }
  | { type: "card"; card: Card }
  | { type: "answer"; text: string }
  | { type: "error"; message: string }
  | { type: "done"; processing_time: string };

export interface UserMessage {
  id: string;
  role: "user";
  text: string;
}

export interface BotMessage {
  id: string;
  role: "bot";
  text: string;
  steps: ToolStep[];
  cards: Card[];
  status: "pending" | "done" | "error";
  processingTime?: string;
}

export type ChatMessage = UserMessage | BotMessage;

/** A saved chat (row in the Supabase `conversations` table). */
export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}
