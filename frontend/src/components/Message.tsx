import { CircleAlert } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import { CardGrid } from "./cards/CardGrid";
import { LogoMark } from "./Logo";
import { Markdown } from "./Markdown";
import { ToolSteps } from "./ToolSteps";
import styles from "./chat.module.css";

export function Message({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className={styles.userRow}>
        <div className={styles.userBubble}>{message.text}</div>
      </div>
    );
  }

  const working = message.status === "pending";
  return (
    <div className={styles.botRow}>
      <div className={styles.botAvatar}>
        <LogoMark size={22} />
      </div>
      <div className={styles.botBody}>
        <ToolSteps steps={message.steps} working={working} />
        {working && !message.text && (
          <div className={styles.thinking} aria-label="TerpAdvisor is thinking">
            <span />
            <span />
            <span />
          </div>
        )}
        {message.status === "error" ? (
          <div className={styles.errorBox} role="alert">
            <CircleAlert size={16} />
            <span>{message.text}</span>
          </div>
        ) : (
          message.text && <Markdown text={message.text} />
        )}
        <CardGrid cards={message.cards} />
      </div>
    </div>
  );
}
