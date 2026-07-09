import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  text?: string;
}

export function LoadingSpinner({ text = "Loading..." }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center h-32">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      {text && <p className="ml-2 text-sm text-muted-foreground">{text}</p>}
    </div>
  );
}

export function PageLoading({ text = "Loading..." }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      {text && <p className="ml-2 text-sm text-muted-foreground">{text}</p>}
    </div>
  );
}
