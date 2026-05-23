import * as React from "react";
import { 
  BrowserRouter as Router, 
  Routes, 
  Route, 
  Navigate 
} from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./screens/Dashboard";
import { People } from "./screens/People";
import { Settings } from "./screens/Settings";
import { Meetings } from "./screens/Meetings";
import { MeetingDetail } from "./screens/MeetingDetail";
import { CommitmentDetail } from "./screens/CommitmentDetail";
import { Login } from "./screens/Login";
import { Register } from "./screens/Register";
import { ConnectSlack } from "./screens/onboarding/ConnectSlack";
import { ImportTracker } from "./screens/onboarding/ImportTracker";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Onboarding */}
            <Route path="/onboarding/slack" element={<ConnectSlack />} />
            <Route path="/onboarding/import" element={<ImportTracker />} />
            <Route path="/onboarding/review" element={<div className="p-20 text-center font-black text-2xl uppercase tracking-tighter">Extraction Review (Coming Soon)</div>} />
            
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            <Route 
              path="/dashboard" 
              element={
                <ProtectedRoute>
                  <AppShell>
                    <Dashboard />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/commitments/:id" 
              element={
                <ProtectedRoute>
                  <AppShell>
                    <CommitmentDetail />
                  </AppShell>
                </ProtectedRoute>
              } 
            />
            
            <Route path="/meetings" element={<ProtectedRoute><AppShell><Meetings /></AppShell></ProtectedRoute>} />
            <Route path="/meetings/:id" element={<ProtectedRoute><AppShell><MeetingDetail /></AppShell></ProtectedRoute>} />
            <Route path="/people" element={<ProtectedRoute><AppShell><People /></AppShell></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><AppShell><Settings /></AppShell></ProtectedRoute>} />
          </Routes>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}
