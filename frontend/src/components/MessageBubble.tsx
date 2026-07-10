import { CitationData } from "@/hooks/useChat";
import CitationTooltip from "./CitationTooltip";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DOMPurify from "dompurify";

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
      return (
        <span key={i} className="inline-flex items-center justify-center h-4 min-w-4 px-1 rounded-full bg-primary/15 text-primary text-[10px] font-semibold align-super mx-0.5">
          {idx}
        </span>
      );
    }
    const sanitized = DOMPurify.sanitize(part);
    return (
      <span key={i}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ children }) => <>{children}</>,
            code: ({ className, children, ...props }) => {
              const isInline = !className;
              if (isInline) {
                return (
                  <code className="bg-background/80 rounded px-1 py-0.5 text-[13px] font-mono" {...props}>
                    {children}
                  </code>
                );
              }
              return (
                <pre className="bg-background/80 rounded-md p-3 overflow-x-auto my-2 text-[13px]">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              );
            },
          }}
        >
          {sanitized}
        </ReactMarkdown>
      </span>
    );
  });
}

export default function MessageBubble({ role, content, citations, grounding_failure }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-neutral-800 text-white"
            : "bg-muted"
        }`}
      >
        {isUser ? (
          <div>{content}</div>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-transparent prose-pre:p-0 prose-code:before:content-none prose-code:after:content-none">
            {renderContent(content, citations)}
          </div>
        )}
        {grounding_failure && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 italic">
            ⚠ The answer may not be fully grounded in the provided documents.
          </p>
        )}
      </div>
    </div>
  );
}
