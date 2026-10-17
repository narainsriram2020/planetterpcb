import type { Metadata } from "next";

// The chat page is a client component, so its metadata lives here.
export const metadata: Metadata = {
  title: "Chat",
  description: "Ask TerpGuide about any UMD course or professor and get an answer backed by PlanetTerp grade data.",
  alternates: { canonical: "/chat" },
  openGraph: { url: "/chat" },
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return children;
}
