import { FileQuestion } from "lucide-react";

interface GroundingFailureProps {
  onRetry?: () => void;
}

export default function GroundingFailure({ onRetry }: GroundingFailureProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <FileQuestion className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold mb-2">No Relevant Documents Found</h3>
      <p className="text-sm text-muted-foreground max-w-md mb-6">
        The current documents don't contain enough information to answer your question.
        Try rephrasing your question, or upload more relevant documents to this trial.
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-sm text-primary hover:text-primary/80 underline underline-offset-2"
        >
          Ask a different question
        </button>
      )}
    </div>
  );
}
