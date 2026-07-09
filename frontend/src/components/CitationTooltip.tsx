import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface CitationTooltipProps {
  index: number;
  content_excerpt: string | null;
  page_number: number | null;
}

export default function CitationTooltip({ index, content_excerpt, page_number }: CitationTooltipProps) {
  return (
    <TooltipProvider>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          <sup className="text-primary cursor-pointer hover:text-primary/80 text-xs font-medium">
            [{index}]
          </sup>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm text-sm">
          <p className="text-xs text-muted-foreground mb-1">
            Source [{index}]{page_number != null ? ` · Page ${page_number}` : ""}
          </p>
          <p className="text-xs leading-relaxed">
            {content_excerpt || "No preview available"}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
