import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import BillEditor from "./pages/BillEditor";
import GroupDetail from "./pages/GroupDetail";
import Groups from "./pages/Groups";
import Login from "./pages/Login";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <Spinner />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Groups />
          </RequireAuth>
        }
      />
      <Route
        path="/groups/:gid"
        element={
          <RequireAuth>
            <GroupDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/groups/:gid/bills/:bid"
        element={
          <RequireAuth>
            <BillEditor />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
