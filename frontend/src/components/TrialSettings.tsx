import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { AlertDialog } from "@/components/ui/alert-dialog";
import { Loader2, Save, Check, Trash2 } from "lucide-react";

interface Settings {
  llm_model: string | null;
  top_k_retrieval: number;
  top_n_rerank: number;
  chunk_size: number;
  chunk_overlap: number;
  cohere_rerank_model: string | null;
  evaluation_threshold: number;
  status: string;
}

interface TrialSettingsProps {
  trialId: string;
  isAdmin: boolean;
  isCreator: boolean;
}

export default function TrialSettings({ trialId, isAdmin, isCreator }: TrialSettingsProps) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [llmModel, setLlmModel] = useState("");
  const [topK, setTopK] = useState(10);
  const [topN, setTopN] = useState(5);
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [cohereModel, setCohereModel] = useState("");
  const [evalThreshold, setEvalThreshold] = useState(0.7);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<Settings>(`/api/trials/${trialId}/settings`);
      setLlmModel(data.llm_model ?? "");
      setTopK(data.top_k_retrieval);
      setTopN(data.top_n_rerank);
      setChunkSize(data.chunk_size);
      setChunkOverlap(data.chunk_overlap);
      setCohereModel(data.cohere_rerank_model ?? "");
      setEvalThreshold(data.evaluation_threshold);
    } catch {
      // handled by api client
    } finally {
      setLoading(false);
    }
  }, [trialId]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      await api.put<Settings>(`/api/trials/${trialId}/settings`, {
        llm_model: llmModel || null,
        top_k_retrieval: topK,
        top_n_rerank: topN,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        cohere_rerank_model: cohereModel || null,
        evaluation_threshold: evalThreshold,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Trial Settings</h3>
        <p className="text-sm text-muted-foreground">
          Configure RAG pipeline parameters for this trial. These override the system defaults.
        </p>
      </div>

      <Separator />

      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="llm_model">LLM Model</Label>
            <Input
              id="llm_model"
              placeholder="gpt-4o-mini (default)"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">OpenAI model for answer generation. Leave empty for system default.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cohere_model">Cohere Rerank Model</Label>
            <Input
              id="cohere_model"
              placeholder="rerank-v3.5 (default)"
              value={cohereModel}
              onChange={(e) => setCohereModel(e.target.value)}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">Leave empty for system default.</p>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="top_k">Top-K Retrieval</Label>
            <Input
              id="top_k"
              type="number"
              min={1}
              max={100}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">Number of chunks to retrieve from vector search.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="top_n">Top-N Rerank</Label>
            <Input
              id="top_n"
              type="number"
              min={1}
              max={50}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">Number of chunks passed to the LLM after reranking.</p>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="chunk_size">Chunk Size</Label>
            <Input
              id="chunk_size"
              type="number"
              min={100}
              max={4000}
              value={chunkSize}
              onChange={(e) => setChunkSize(Number(e.target.value))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">Document chunk size in tokens.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="chunk_overlap">Chunk Overlap</Label>
            <Input
              id="chunk_overlap"
              type="number"
              min={0}
              max={1000}
              value={chunkOverlap}
              onChange={(e) => setChunkOverlap(Number(e.target.value))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">Overlap between consecutive chunks in tokens.</p>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="eval_threshold">Evaluation Threshold</Label>
            <Input
              id="eval_threshold"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={evalThreshold}
              onChange={(e) => setEvalThreshold(Number(e.target.value))}
              disabled={!isAdmin}
            />
            <p className="text-xs text-muted-foreground">Minimum acceptable faithfulness score (0.0 - 1.0).</p>
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {isAdmin && (
        <div className="flex items-center gap-3">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : saved ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Saved
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Settings
              </>
            )}
          </Button>
        </div>
      )}

      {!isAdmin && (
        <p className="text-sm text-muted-foreground italic">
          Only admins can modify trial settings.
        </p>
      )}

      {isCreator && (
        <>
          <Separator />
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-destructive">Danger Zone</h3>
            <p className="text-sm text-muted-foreground">
              Deleting this trial will permanently remove all documents, chunks, and settings.
              This action cannot be undone.
            </p>
            <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Trial
            </Button>
          </div>
        </>
      )}

      <AlertDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Trial?"
        description="Are you sure you want to delete this trial? All documents, chunks, files, and settings will be permanently removed. This action cannot be undone."
        actionLabel="Delete Trial"
        actionVariant="destructive"
        loading={deleting}
        onAction={async () => {
          setDeleting(true);
          try {
            await api.delete(`/api/trials/${trialId}`);
            navigate("/trials");
          } catch {
            setDeleting(false);
            setDeleteOpen(false);
            setError("Failed to delete trial. Please try again.");
          }
        }}
      />
    </div>
  );
}
