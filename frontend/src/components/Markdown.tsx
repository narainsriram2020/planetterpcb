import ReactMarkdown from "react-markdown";
import styles from "./chat.module.css";

// The agent is asked for light formatting only; anything else is unwrapped to text.
const ALLOWED = ["p", "strong", "em", "ul", "ol", "li", "a", "br", "code"];

export function Markdown({ text }: { text: string }) {
  return (
    <div className={styles.prose}>
      <ReactMarkdown
        allowedElements={ALLOWED}
        unwrapDisallowed
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
