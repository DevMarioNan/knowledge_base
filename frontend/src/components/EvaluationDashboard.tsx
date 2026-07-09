import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronRight } from "lucide-react";

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

interface RunDetail extends Run {
  question_scores: QuestionScore[];
}

interface QuestionScore {
  id: string;
  question_id: string;
  question_text: string;
  ground_truth: string;
  answer: string;
  contexts: string[];
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
  context_recall: number | null;
}

const METRIC_LABELS: Record<string, string> = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  context_precision: "Context Precision",
  context_recall: "Context Recall",
};

const METRIC_COLORS: Record<string, string> = {
  faithfulness: "#2563eb",
  answer_relevancy: "#16a34a",
  context_precision: "#d97706",
  context_recall: "#9333ea",
};

function MetricBadge({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <span className="text-muted-foreground text-sm">-</span>;
  const color = value >= 0.7 ? "text-green-600" : value >= 0.4 ? "text-amber-600" : "text-red-600";
  return <span className={`text-sm font-medium ${color}`}>{value.toFixed(3)}</span>;
}

function MetricTrend({ current, previous }: { current: number | null; previous: number | null }) {
  if (current === null || previous === null) return <Minus className="h-4 w-4 text-muted-foreground" />;
  const diff = current - previous;
  if (diff > 0.01) return <TrendingUp className="h-4 w-4 text-green-600" />;
  if (diff < -0.01) return <TrendingDown className="h-4 w-4 text-red-600" />;
  return <Minus className="h-4 w-4 text-muted-foreground" />;
}

function QuestionRow({ question }: { question: QuestionScore }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <TableRow className="align-top cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <TableCell className="text-sm font-medium">
          <div className="flex items-center gap-1">
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            )}
            <span className="truncate">{question.question_text}</span>
          </div>
        </TableCell>
        <TableCell><MetricBadge value={question.faithfulness} /></TableCell>
        <TableCell><MetricBadge value={question.answer_relevancy} /></TableCell>
        <TableCell><MetricBadge value={question.context_precision} /></TableCell>
        <TableCell><MetricBadge value={question.context_recall} /></TableCell>
      </TableRow>
      {expanded && (
        <TableRow key={`detail-${question.id}`}>
          <TableCell colSpan={5} className="bg-muted/30 p-0">
            <div className="px-6 py-4 space-y-4 border-t">
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Model Answer</h4>
                <p className="text-sm whitespace-pre-wrap">{question.answer}</p>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Ground Truth</h4>
                <p className="text-sm whitespace-pre-wrap">{question.ground_truth}</p>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
                  Retrieved Contexts ({question.contexts.length})
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {question.contexts.map((ctx, i) => (
                    <p key={i} className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
                      <span className="font-medium text-foreground">[{i + 1}]</span> {ctx}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

interface Props {
  trialId: string;
  refreshKey: number;
}

export default function EvaluationDashboard({ trialId, refreshKey }: Props) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<Run[]>(`/api/trials/${trialId}/evaluation/runs`);
      setRuns(data);
    } finally {
      setLoading(false);
    }
  }, [trialId]);

  const fetchRunDetail = useCallback(async (runId: string) => {
    try {
      const data = await api.get<RunDetail>(`/api/trials/${trialId}/evaluation/runs/${runId}`);
      setSelectedRun(data);
    } catch {}
  }, [trialId]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns, refreshKey]);

  useEffect(() => {
    if (selectedRunId) {
      fetchRunDetail(selectedRunId);
    } else {
      setSelectedRun(null);
    }
  }, [selectedRunId, fetchRunDetail]);

  const completedRuns = runs.filter((r) => r.status === "completed" && r.overall_scores);

  const chartData = [...completedRuns].reverse().map((r) => ({
    date: new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    ...r.overall_scores,
  }));

  const latestRun = completedRuns[0];
  const previousRun = completedRuns[1];

  if (loading) {
    return <p className="text-muted-foreground text-sm">Loading evaluation data...</p>;
  }

  if (completedRuns.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <p>No completed evaluation runs yet.</p>
          <p className="text-sm mt-1">Create a dataset with questions and run an evaluation to see results here.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      {latestRun && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(METRIC_LABELS).map(([key, label]) => {
            const current = latestRun.overall_scores?.[key] ?? null;
            const previous = previousRun?.overall_scores?.[key] ?? null;
            return (
              <Card key={key}>
                <CardHeader className="pb-2 pt-4 px-4">
                  <div className="flex items-center justify-between">
                    <CardDescription className="text-xs">{label}</CardDescription>
                    <MetricTrend current={current} previous={previous} />
                  </div>
                  <CardTitle className={`text-2xl ${
                    current !== null && current >= 0.7 ? "text-green-600" :
                    current !== null && current >= 0.4 ? "text-amber-600" :
                    "text-red-600"
                  }`}>
                    {current !== null ? (current * 100).toFixed(0) + "%" : "-"}
                  </CardTitle>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      )}

      {/* Trend chart */}
      {chartData.length >= 2 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Score Trends Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickFormatter={(v) => (v * 100).toFixed(0) + "%"} />
                  <Tooltip formatter={(value) => (Number(value) * 100).toFixed(1) + "%"} />
                  <Legend />
                  {Object.entries(METRIC_COLORS).map(([key, color]) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={color}
                      name={METRIC_LABELS[key]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Run selector */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Evaluation Runs
        </h3>
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Dataset</TableHead>
                <TableHead>Questions</TableHead>
                <TableHead>Faithfulness</TableHead>
                <TableHead>Relevancy</TableHead>
                <TableHead>Precision</TableHead>
                <TableHead>Recall</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow
                  key={run.id}
                  className={`cursor-pointer ${selectedRunId === run.id ? "bg-muted/50" : ""}`}
                  onClick={() => setSelectedRunId(run.id)}
                >
                  <TableCell className="text-sm">
                    {new Date(run.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {run.dataset_name}
                  </TableCell>
                  <TableCell className="text-sm">{run.question_count}</TableCell>
                  <TableCell><MetricBadge value={run.overall_scores?.faithfulness ?? null} /></TableCell>
                  <TableCell><MetricBadge value={run.overall_scores?.answer_relevancy ?? null} /></TableCell>
                  <TableCell><MetricBadge value={run.overall_scores?.context_precision ?? null} /></TableCell>
                  <TableCell><MetricBadge value={run.overall_scores?.context_recall ?? null} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Per-question drill-down */}
      {selectedRun && selectedRun.question_scores.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Per-Question Scores
          </h3>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[25%]">Question</TableHead>
                  <TableHead>Faithfulness</TableHead>
                  <TableHead>Relevancy</TableHead>
                  <TableHead>Precision</TableHead>
                  <TableHead>Recall</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {selectedRun.question_scores.map((qs) => (
                  <QuestionRow key={qs.id} question={qs} />
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
