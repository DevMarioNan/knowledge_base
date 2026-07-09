import { CitationData } from "@/hooks/useChat";

interface SourcePanelProps {
  citations: CitationData[];
  onClose: () => void;
}

export default function SourcePanel({ citations, onClose }: SourcePanelProps) {
  if (citations.length === 0) return null;

  return (
    <div className="border-l bg-muted/30 p-4 w-80 overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Sources</h3>
        <button
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Close
        </button>
      </div>

      <div className="space-y-3">
        {citations.map((cit) => (
          <div key={cit.citation_index} className="bg-background rounded border p-3 text-xs">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-bold text-primary">[{cit.citation_index}]</span>
              {cit.page_number != null && (
                <span className="text-muted-foreground">Page {cit.page_number}</span>
              )}
              {cit.relevance_score != null && (
                <span className="text-muted-foreground ml-auto">
                  {(cit.relevance_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
            <p className="text-muted-foreground leading-relaxed">
              {cit.content_excerpt || "No preview"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
