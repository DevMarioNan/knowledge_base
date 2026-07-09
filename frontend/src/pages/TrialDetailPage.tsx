import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import MembersList from "@/components/MembersList";
import DocumentsList from "@/components/DocumentsList";
import TrialSettings from "@/components/TrialSettings";
import ChatPanel from "@/components/ChatPanel";
import EvaluationDashboard from "@/components/EvaluationDashboard";
import EvaluationDatasetManager from "@/components/EvaluationDatasetManager";
import { ArrowLeft, FileText, MessageSquare, Users, Settings, BarChart3 } from "lucide-react";

interface TrialDetail {
  id: string;
  name: string;
  description: string | null;
  created_by: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export default function TrialDetailPage() {
  const { trialId } = useParams<{ trialId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [trial, setTrial] = useState<TrialDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [evalRefreshKey, setEvalRefreshKey] = useState(0);

  const fetchTrial = useCallback(async () => {
    if (!trialId) return;
    setLoading(true);
    try {
      const data = await api.get<TrialDetail>(`/api/trials/${trialId}`);
      setTrial(data);
    } catch {
      navigate("/trials");
    } finally {
      setLoading(false);
    }
  }, [trialId, navigate]);

  useEffect(() => {
    fetchTrial();
  }, [fetchTrial]);

  if (loading || !trial) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading trial...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/trials")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{trial.name}</h1>
          {trial.description && (
            <p className="text-muted-foreground">{trial.description}</p>
          )}
        </div>
      </div>

      <Separator />

      <Tabs defaultValue="documents">
        <TabsList>
          <TabsTrigger value="chat">
            <MessageSquare className="h-4 w-4 mr-2" />
            Chat
          </TabsTrigger>
          <TabsTrigger value="documents">
            <FileText className="h-4 w-4 mr-2" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="members">
            <Users className="h-4 w-4 mr-2" />
            Members
          </TabsTrigger>
          <TabsTrigger value="evaluation">
            <BarChart3 className="h-4 w-4 mr-2" />
            Evaluation
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="py-4">
          <ChatPanel trialId={trial.id} />
        </TabsContent>

        <TabsContent value="documents" className="py-4">
          <DocumentsList trialId={trial.id} />
        </TabsContent>

        <TabsContent value="members" className="py-4">
          <MembersList trialId={trial.id} currentUserId={user!.id} />
        </TabsContent>

        <TabsContent value="evaluation" className="py-4 space-y-6">
          <EvaluationDatasetManager trialId={trial.id} onRunCompleted={() => setEvalRefreshKey((k) => k + 1)} />
          <div className="border-t pt-6">
            <h2 className="text-lg font-semibold mb-4">Dashboard</h2>
            <EvaluationDashboard trialId={trial.id} refreshKey={evalRefreshKey} />
          </div>
        </TabsContent>

        <TabsContent value="settings" className="py-4">
          <TrialSettings trialId={trial.id} isAdmin={trial.role === "admin"} isCreator={trial.created_by === user!.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
