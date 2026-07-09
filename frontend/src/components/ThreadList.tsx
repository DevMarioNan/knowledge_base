import { useState } from "react";
import { ThreadData } from "@/hooks/useChat";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { AlertDialog } from "@/components/ui/alert-dialog";

interface ThreadListProps {
  threads: ThreadData[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => Promise<void>;
}

export default function ThreadList({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
}: ThreadListProps) {
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const threadToDelete = threads.find((t) => t.id === deletingThreadId);

  const handleConfirmDelete = async () => {
    if (!deletingThreadId) return;
    setDeleteLoading(true);
    try {
      await onDeleteThread(deletingThreadId);
    } finally {
      setDeleteLoading(false);
      setDeletingThreadId(null);
    }
  };

  return (
    <div className="w-64 border-r bg-muted/20 flex flex-col h-full">
      <div className="p-3 border-b">
        <button
          onClick={onCreateThread}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {threads.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-4">
            No conversations yet
          </p>
        )}
        {threads.map((thread) => (
          <div
            key={thread.id}
            className={`group flex items-center gap-1 px-3 py-2 text-sm rounded-md transition-colors ${
              thread.id === activeThreadId
                ? "bg-accent text-accent-foreground"
                : "hover:bg-muted"
            }`}
          >
            <button
              onClick={() => onSelectThread(thread.id)}
              className="flex items-center gap-2 flex-1 min-w-0 text-left"
            >
              <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{thread.title}</span>
            </button>
            <button
              onClick={() => setDeletingThreadId(thread.id)}
              className="h-6 w-6 shrink-0 flex items-center justify-center rounded-md opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-all"
              title="Delete conversation"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>

      <AlertDialog
        open={deletingThreadId !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingThreadId(null);
        }}
        title="Delete conversation?"
        description={
          threadToDelete
            ? `Are you sure you want to delete "${threadToDelete.title}"? All messages in this conversation will be permanently removed.`
            : "Are you sure? All messages will be permanently removed."
        }
        actionLabel="Delete"
        actionVariant="destructive"
        loading={deleteLoading}
        onAction={handleConfirmDelete}
      />
    </div>
  );
}
