import { CitationData } from "@/hooks/useChat";
import { FileText } from "lucide-react";

interface SourcePanelProps {
  citations: CitationData[];
  onClose: () => void;
}

export default function SourcePanel({ citations, onClose }: SourcePanelProps) {
  if (citations.length === 0) return null;

  return (
    <div className="border-l bg-muted/30 w-80 flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="text-sm font-semibold">Sources</h3>
        <button
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {citations.map((cit) => (
          <div
            key={cit.citation_index}
            className="bg-background rounded-lg border p-3 text-xs space-y-2 hover:border-primary/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary/15 text-primary text-[10px] font-bold shrink-0">
                {cit.citation_index}
              </span>
              <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="text-muted-foreground truncate">
                {cit.document_id.slice(0, 8)}…
              </span>
              {cit.page_number != null && (
                <span className="text-muted-foreground ml-auto shrink-0">
                  p.{cit.page_number}
                </span>
              )}
            </div>

            {cit.content_excerpt && (
              <p className="text-muted-foreground leading-relaxed line-clamp-3 border-l-2 border-primary/20 pl-2">
                "{cit.content_excerpt}"
              </p>
            )}

            <div className="flex items-center gap-2 pt-1">
              {cit.relevance_score != null && (
                <span className="text-[10px] text-muted-foreground">
                  Relevance: {(cit.relevance_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
