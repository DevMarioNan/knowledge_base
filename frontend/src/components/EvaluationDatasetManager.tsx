import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Play, Loader2 } from "lucide-react";

interface Dataset {
  id: string;
  name: string;
  description: string | null;
  question_count: number;
  created_at: string;
}

interface Question {
  id: string;
  question: string;
  ground_truth_answer: string;
  created_at: string;
}

interface Run {
  id: string;
  dataset_id: string;
  dataset_name: string;
  status: string;
  overall_scores: Record<string, number> | null;
  created_at: string;
  completed_at: string | null;
  question_count: number;
}

interface Props {
  trialId: string;
  onRunCompleted: () => void;
}

export default function EvaluationDatasetManager({ trialId, onRunCompleted }: Props) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showQuestionDialog, setShowQuestionDialog] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [datasetDesc, setDatasetDesc] = useState("");
  const [questionText, setQuestionText] = useState("");
  const [groundTruth, setGroundTruth] = useState("");
  const [running, setRunning] = useState<string | null>(null);
  const runningRef = useRef<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoadingDatasets(true);
    try {
      const data = await api.get<Dataset[]>(`/api/trials/${trialId}/evaluation/datasets`);
      setDatasets(data);
    } finally {
      setLoadingDatasets(false);
    }
  }, [trialId]);

  const fetchQuestions = useCallback(async (datasetId: string) => {
    setLoadingQuestions(true);
    try {
      const data = await api.get<Question[]>(
        `/api/trials/${trialId}/evaluation/datasets/${datasetId}/questions`
      );
      setQuestions(data);
    } finally {
      setLoadingQuestions(false);
    }
  }, [trialId]);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await api.get<Run[]>(`/api/trials/${trialId}/evaluation/runs`);
      setRuns(data);
    } catch {}
  }, [trialId]);

  useEffect(() => {
    fetchDatasets();
    fetchRuns();
  }, [fetchDatasets, fetchRuns]);

  useEffect(() => {
    if (selectedDatasetId) {
      fetchQuestions(selectedDatasetId);
    } else {
      setQuestions([]);
    }
  }, [selectedDatasetId, fetchQuestions]);

  const handleCreateDataset = async () => {
    if (!datasetName.trim()) return;
    await api.post(`/api/trials/${trialId}/evaluation/datasets`, {
      name: datasetName,
      description: datasetDesc || null,
    });
    setDatasetName("");
    setDatasetDesc("");
    setShowCreateDialog(false);
    await fetchDatasets();
  };

  const handleDeleteDataset = async (datasetId: string) => {
    await api.delete(`/api/trials/${trialId}/evaluation/datasets/${datasetId}`);
    if (selectedDatasetId === datasetId) {
      setSelectedDatasetId(null);
    }
    await fetchDatasets();
  };

  const handleCreateQuestion = async () => {
    if (!questionText.trim() || !groundTruth.trim() || !selectedDatasetId) return;
    await api.post(
      `/api/trials/${trialId}/evaluation/datasets/${selectedDatasetId}/questions`,
      { question: questionText, ground_truth_answer: groundTruth }
    );
    setQuestionText("");
    setGroundTruth("");
    setShowQuestionDialog(false);
    await fetchQuestions(selectedDatasetId);
  };

  const handleUpdateQuestion = async () => {
    if (!editingQuestion || !selectedDatasetId) return;
    await api.put(
      `/api/trials/${trialId}/evaluation/datasets/${selectedDatasetId}/questions/${editingQuestion.id}`,
      { question: questionText, ground_truth_answer: groundTruth }
    );
    setEditingQuestion(null);
    setQuestionText("");
    setGroundTruth("");
    setShowQuestionDialog(false);
    await fetchQuestions(selectedDatasetId);
  };

  const handleDeleteQuestion = async (questionId: string) => {
    if (!selectedDatasetId) return;
    await api.delete(
      `/api/trials/${trialId}/evaluation/datasets/${selectedDatasetId}/questions/${questionId}`
    );
    const data = await api.get<Dataset[]>(`/api/trials/${trialId}/evaluation/datasets`);
    setDatasets(data);
    await fetchQuestions(selectedDatasetId);
  };

  const handleRun = async (datasetId: string) => {
    setRunning(datasetId);
    runningRef.current = datasetId;
    try {
      await api.post(`/api/trials/${trialId}/evaluation/runs`, { dataset_id: datasetId });
    } catch {
      setRunning(null);
      runningRef.current = null;
    }
  };

  // Poll for async run completion
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(async () => {
      try {
        const data = await api.get<Run[]>(`/api/trials/${trialId}/evaluation/runs`);
        const datasetRuns = data.filter((r) => r.dataset_id === running);
        const latestRun = datasetRuns[0];
        if (latestRun && (latestRun.status === "completed" || latestRun.status === "failed")) {
          setRunning(null);
          runningRef.current = null;
          setRuns(data);
          onRunCompleted();
        }
      } catch {
        // ignore polling errors
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [running, trialId, onRunCompleted]);

  const openEditQuestion = (q: Question) => {
    setEditingQuestion(q);
    setQuestionText(q.question);
    setGroundTruth(q.ground_truth_answer);
    setShowQuestionDialog(true);
  };

  const openAddQuestion = () => {
    setEditingQuestion(null);
    setQuestionText("");
    setGroundTruth("");
    setShowQuestionDialog(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Evaluation Datasets</h3>
        <Button onClick={() => setShowCreateDialog(true)} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          New Dataset
        </Button>
      </div>

      {loadingDatasets ? (
        <p className="text-muted-foreground text-sm">Loading datasets...</p>
      ) : datasets.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>No evaluation datasets yet. Create one to start measuring RAG pipeline quality.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {datasets.map((ds) => (
            <Card
              key={ds.id}
              className={`cursor-pointer transition-colors ${
                selectedDatasetId === ds.id ? "ring-2 ring-primary" : ""
              }`}
              onClick={() => setSelectedDatasetId(ds.id)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base">{ds.name}</CardTitle>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); handleRun(ds.id); }}
                      disabled={running === ds.id || ds.question_count === 0}
                    >
                      {running === ds.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive"
                      onClick={(e) => { e.stopPropagation(); handleDeleteDataset(ds.id); }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground mb-1">
                  {ds.description || "No description"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {ds.question_count} question{ds.question_count !== 1 ? "s" : ""}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {selectedDatasetId && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Questions
            </h4>
            <Button onClick={openAddQuestion} size="sm" variant="outline">
              <Plus className="h-4 w-4 mr-1" />
              Add Question
            </Button>
          </div>

          {loadingQuestions ? (
            <p className="text-muted-foreground text-sm">Loading questions...</p>
          ) : questions.length === 0 ? (
            <Card>
              <CardContent className="py-6 text-center text-muted-foreground text-sm">
                <p>No questions in this dataset. Add a question + ground truth pair.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40%]">Question</TableHead>
                    <TableHead className="w-[40%]">Ground Truth Answer</TableHead>
                    <TableHead className="w-[20%]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {questions.map((q) => (
                    <TableRow key={q.id}>
                      <TableCell className="font-medium text-sm">{q.question}</TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                        {q.ground_truth_answer}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => openEditQuestion(q)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive"
                            onClick={() => handleDeleteQuestion(q.id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}

      {runs.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Recent Runs
          </h4>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Questions</TableHead>
                  <TableHead>Faithfulness</TableHead>
                  <TableHead>Relevancy</TableHead>
                  <TableHead>Precision</TableHead>
                  <TableHead>Recall</TableHead>
                </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.slice(0, 10).map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="text-sm">
                        {new Date(run.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{run.dataset_name}</TableCell>
                      <TableCell>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          run.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : run.status === "running"
                            ? "bg-blue-100 text-blue-700"
                            : run.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-700"
                        }`}>
                          {run.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">{run.question_count}</TableCell>
                    <TableCell className="text-sm">{run.overall_scores?.faithfulness?.toFixed(3) ?? "-"}</TableCell>
                    <TableCell className="text-sm">{run.overall_scores?.answer_relevancy?.toFixed(3) ?? "-"}</TableCell>
                    <TableCell className="text-sm">{run.overall_scores?.context_precision?.toFixed(3) ?? "-"}</TableCell>
                    <TableCell className="text-sm">{run.overall_scores?.context_recall?.toFixed(3) ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Create Dataset Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Evaluation Dataset</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input value={datasetName} onChange={(e) => setDatasetName(e.target.value)} placeholder="e.g., Adverse Events QA" />
            </div>
            <div>
              <label className="text-sm font-medium">Description</label>
              <Input value={datasetDesc} onChange={(e) => setDatasetDesc(e.target.value)} placeholder="Optional description" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateDataset} disabled={!datasetName.trim()}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add/Edit Question Dialog */}
      <Dialog open={showQuestionDialog} onOpenChange={setShowQuestionDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingQuestion ? "Edit Question" : "Add Question"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Question</label>
              <textarea
                className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder="e.g., What are the common adverse events?"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Ground Truth Answer</label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={groundTruth}
                onChange={(e) => setGroundTruth(e.target.value)}
                placeholder="The expected correct answer..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowQuestionDialog(false)}>Cancel</Button>
            <Button onClick={editingQuestion ? handleUpdateQuestion : handleCreateQuestion} disabled={!questionText.trim() || !groundTruth.trim()}>
              {editingQuestion ? "Save" : "Add"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
