import { CitationData } from "@/hooks/useChat";
import CitationTooltip from "./CitationTooltip";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  citations: CitationData[];
  grounding_failure: boolean;
}

function renderContent(text: string, citations: CitationData[]) {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/\[(\d+)\]/);
    if (match) {
      const idx = parseInt(match[1], 10);
      const citation = citations.find((c) => c.citation_index === idx);
      if (citation) {
        return (
          <CitationTooltip
            key={i}
            index={idx}
            content_excerpt={citation.content_excerpt}
            page_number={citation.page_number}
          />
        );
      }
      return <sup key={i} className="text-xs text-muted-foreground">[{idx}]</sup>;
    }
    return <span key={i}>{part}</span>;
  });
}

export default function MessageBubble({ role, content, citations, grounding_failure }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap leading-relaxed">
          {isUser ? content : renderContent(content, citations)}
        </p>
        {grounding_failure && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 italic">
            ⚠ The answer may not be fully grounded in the provided documents.
          </p>
        )}
      </div>
    </div>
  );
}
