import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import TrialsListPage from "@/pages/TrialsListPage";
import TrialDetailPage from "@/pages/TrialDetailPage";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/"
            element={<Navigate to="/trials" replace />}
          />
          <Route
            path="/trials"
            element={
              <ProtectedLayout>
                <TrialsListPage />
              </ProtectedLayout>
            }
          />
          <Route
            path="/trials/:trialId"
            element={
              <ProtectedLayout>
                <TrialDetailPage />
              </ProtectedLayout>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
