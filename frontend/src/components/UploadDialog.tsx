import { useState, useRef, useCallback, type DragEvent, type ChangeEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Upload, File, X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface UploadDialogProps {
  trialId: string;
  onUploadComplete: () => void;
}

interface FileEntry {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

const MAX_CONCURRENT = 3;

export default function UploadDialog({ trialId, onUploadComplete }: UploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

  const uploading = entries.some((e) => e.status === "uploading");

  const reset = () => {
    setEntries([]);
  };

  const addFiles = useCallback((list: FileList) => {
    const valid: FileEntry[] = [];
    for (const f of list) {
      if (f.type === "application/pdf") {
        valid.push({ file: f, progress: 0, status: "pending" });
      }
    }
    if (valid.length > 0) {
      setEntries((prev) => [...prev, ...valid]);
    }
  }, []);

  const removeEntry = (i: number) => {
    setEntries((prev) => prev.filter((_, idx) => idx !== i));
  };

  const updateEntry = (i: number, patch: Partial<FileEntry>) => {
    setEntries((prev) => prev.map((e, idx) => (idx === i ? { ...e, ...patch } : e)));
  };

  const onDragOver = (e: DragEvent) => { e.preventDefault(); };

  const onDragEnter = (e: DragEvent) => {
    e.preventDefault();
    dragCounter.current++;
    if (dragCounter.current === 1) {
      setDragOver(true);
    }
  };

  const onDragLeave = (e: DragEvent) => {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setDragOver(false);
    }
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragCounter.current = 0;
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const onSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
    }
    e.target.value = "";
  };

  const handleUpload = async () => {
    const pendingIndices = entries.reduce<number[]>((acc, e, i) => {
      if (e.status === "pending") acc.push(i);
      return acc;
    }, []);

    if (pendingIndices.length === 0) return;

    let successCount = 0;

    for (let start = 0; start < pendingIndices.length; start += MAX_CONCURRENT) {
      const batch = pendingIndices.slice(start, start + MAX_CONCURRENT);
      const results = await Promise.allSettled(
        batch.map(async (i) => {
          const entry = entries[i];
          updateEntry(i, { status: "uploading", progress: 0 });
          const formData = new FormData();
          formData.append("file", entry.file);
          await api.upload(`/api/trials/${trialId}/documents`, formData, (pct) => {
            updateEntry(i, { progress: pct });
          });
          updateEntry(i, { status: "done", progress: 100 });
        }),
      );
      results.forEach((r) => {
        if (r.status === "fulfilled") {
          successCount++;
        } else {
          const index = batch[results.indexOf(r)];
          updateEntry(index, {
            status: "error",
            error: r.reason instanceof Error ? r.reason.message : "Upload failed",
          });
        }
      });
    }

    if (successCount === pendingIndices.length) {
      setTimeout(() => {
        setOpen(false);
        reset();
        onUploadComplete();
      }, 1000);
    }
  };

  const pendingCount = entries.filter((e) => e.status === "pending").length;
  const doneCount = entries.filter((e) => e.status === "done").length;
  const errorCount = entries.filter((e) => e.status === "error").length;
  const hasEntries = entries.length > 0;
  const allDone = hasEntries && entries.every((e) => e.status === "done");
  const anyNonPending = entries.some((e) => e.status !== "pending");

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Upload PDFs
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
        </DialogHeader>

        <div
          onDragOver={onDragOver}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !anyNonPending && inputRef.current?.click()}
          className={`
            relative flex flex-col items-center justify-center gap-3 border-2 rounded-lg p-10 cursor-pointer
            transition-all duration-200 ease-in-out select-none
            ${anyNonPending ? "opacity-50 pointer-events-none" : ""}
            ${dragOver
              ? "border-primary scale-[1.02] bg-primary/5 shadow-lg border-solid"
              : "border-dashed border-muted-foreground/25 hover:border-primary/50"
            }
          `}
        >
          <div className="relative">
            <Upload
              className={`h-8 w-8 transition-all duration-200 ${dragOver ? "text-primary scale-110" : "text-muted-foreground"}`}
            />
            {dragOver && (
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-primary" />
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground text-center">
            {dragOver ? "Release to drop your PDFs" : "Drop PDFs here or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground">PDF files up to 50MB each</p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={onSelect}
          />
        </div>

        {hasEntries && (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {entries.map((entry, i) => (
              <div
                key={i}
                className={`flex items-center gap-3 p-3 border rounded-lg transition-colors ${
                  entry.status === "error" ? "border-destructive/30 bg-destructive/5" : ""
                }`}
              >
                <File className="h-5 w-5 shrink-0 text-primary" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm truncate">{entry.file.name}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      ({(entry.file.size / 1024 / 1024).toFixed(1)} MB)
                    </span>
                  </div>
                  {entry.status === "uploading" && (
                    <div className="mt-1.5 w-full bg-muted rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-300 rounded-full"
                        style={{ width: `${Math.max(entry.progress, 2)}%` }}
                      />
                    </div>
                  )}
                  {entry.status === "done" && (
                    <span className="text-xs text-green-600 flex items-center gap-1 mt-1">
                      <CheckCircle2 className="h-3 w-3" /> Uploaded
                    </span>
                  )}
                  {entry.status === "error" && (
                    <span className="text-xs text-destructive flex items-center gap-1 mt-1">
                      <AlertCircle className="h-3 w-3" /> {entry.error || "Upload failed"}
                    </span>
                  )}
                </div>
                {entry.status === "pending" && !uploading && (
                  <button
                    onClick={() => removeEntry(i)}
                    className="shrink-0 p-1 hover:bg-muted rounded transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
                {entry.status === "uploading" && (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
                )}
                {entry.status === "done" && (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
                )}
                {entry.status === "error" && (
                  <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
                )}
              </div>
            ))}
          </div>
        )}

        {hasEntries && !allDone && (
          <p className="text-sm text-muted-foreground text-center">
            {doneCount + entries.filter((e) => e.status === "uploading").length} of {entries.length} processed
            {errorCount > 0 && ` (${errorCount} failed)`}
          </p>
        )}

        {allDone && (
          <p className="text-sm text-green-600 flex items-center gap-2 justify-center">
            <CheckCircle2 className="h-4 w-4" />
            All files uploaded successfully
          </p>
        )}

        {!allDone && hasEntries && (
          <Button
            onClick={handleUpload}
            disabled={uploading || pendingCount === 0}
            className="w-full"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              `Upload ${pendingCount} file${pendingCount > 1 ? "s" : ""}`
            )}
          </Button>
        )}
      </DialogContent>
    </Dialog>
  );
}
