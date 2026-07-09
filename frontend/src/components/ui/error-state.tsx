import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  onBack?: () => void;
}

export function ErrorState({ title = "Something went wrong", message, onRetry, onBack }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-48 border rounded-lg bg-destructive/5">
      <AlertCircle className="h-10 w-10 text-destructive mb-3" />
      <h3 className="text-sm font-medium text-destructive">{title}</h3>
      {message && <p className="text-sm text-muted-foreground mt-1 max-w-md text-center">{message}</p>}
      <div className="flex gap-2 mt-4">
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Try again
          </Button>
        )}
        {onBack && (
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Go back
          </Button>
        )}
      </div>
    </div>
  );
}
