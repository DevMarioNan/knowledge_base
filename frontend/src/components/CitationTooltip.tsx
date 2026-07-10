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
          <span className="inline-flex items-center justify-center h-4 min-w-4 px-1 rounded-full bg-primary/15 text-primary text-[10px] font-semibold leading-none cursor-pointer hover:bg-primary/25 transition-colors align-super mx-0.5">
            {index}
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-primary/20 text-primary text-[10px] font-semibold">
                {index}
              </span>
              <span className="text-xs font-medium">Source {index}</span>
              {page_number != null && (
                <span className="text-xs text-muted-foreground">· Page {page_number}</span>
              )}
            </div>
            {content_excerpt && (
              <p className="text-xs leading-relaxed text-muted-foreground border-l-2 border-primary/30 pl-2 italic">
                "{content_excerpt}"
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
