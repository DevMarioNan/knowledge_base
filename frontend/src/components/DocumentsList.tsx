import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { getErrorMessage } from "@/lib/http";
import UploadDialog from "@/components/UploadDialog";
import { FileText, Trash2, Loader2, AlertCircle } from "lucide-react";

interface DocumentItem {
  id: string;
  trial_id: string;
  filename: string;
  status: string;
  metadata: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

interface DocumentsListProps {
  trialId: string;
}

const POLL_INTERVAL = 3000;
const NON_TERMINAL = new Set(["uploaded", "parsing", "chunking", "embedding"]);

const statusColor: Record<string, string> = {
  uploaded: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  parsing: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  chunking: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  embedding: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  ready: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export default function DocumentsList({ trialId }: DocumentsListProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [hasActive, setHasActive] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setError(null);
    try {
      const data = await api.get<DocumentItem[]>(`/api/trials/${trialId}/documents`);
      setDocuments(data);
      setHasActive(data.some((d) => NON_TERMINAL.has(d.status)));
    } catch (err) {
      if (!hasActive) setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [trialId, hasActive]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    if (!hasActive) return;
    const interval = setInterval(fetchDocuments, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchDocuments, hasActive]);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document? This action cannot be undone.")) return;
    setDeleting((prev) => new Set(prev).add(id));
    try {
      await api.delete(`/api/documents/${id}`);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } finally {
      setDeleting((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  if (loading) {
    return <LoadingSpinner text="Loading documents..." />;
  }

  if (error) {
    return (
      <div className="space-y-4">
        <ErrorState title="Failed to load documents" message={error} onRetry={fetchDocuments} />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          <UploadDialog trialId={trialId} onUploadComplete={fetchDocuments} />
        </div>
        <EmptyState icon={FileText} title="No documents uploaded yet" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <UploadDialog trialId={trialId} onUploadComplete={fetchDocuments} />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Uploaded</TableHead>
            <TableHead className="w-12"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell>
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-sm truncate max-w-[300px]">{doc.filename}</span>
                </div>
                {doc.status === "failed" && doc.error_message && (
                  <p className="text-xs text-red-500 mt-0.5 truncate max-w-[400px]">{doc.error_message}</p>
                )}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Badge className={statusColor[doc.status] ?? ""} variant="outline">
                    {doc.status}
                    {NON_TERMINAL.has(doc.status) && (
                      <Loader2 className="h-3 w-3 ml-1 animate-spin" />
                    )}
                    {doc.status === "failed" && (
                      <AlertCircle className="h-3 w-3 ml-1" />
                    )}
                  </Badge>
                </div>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {new Date(doc.created_at).toLocaleDateString()}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDelete(doc.id)}
                  disabled={deleting.has(doc.id)}
                >
                  {deleting.has(doc.id) ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                  )}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
