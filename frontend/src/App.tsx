import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api/client";
import AgentQueue from "./pages/AgentQueue";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Labeling from "./pages/Labeling";
import Settings from "./pages/Settings";

export default function App() {
  const [pending, setPending] = useState(0);
  const location = useLocation();
  useEffect(() => {
    api.queue("pending").then((q) => setPending(q.length)).catch(() => undefined);
  }, [location]);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">Lumo Support <span>· Bias-Labor (fiktiver Testshop)</span></div>
        <nav className="nav">
          <NavLink to="/chat">Kundenchat</NavLink>
          <NavLink to="/queue">Agent-Queue{pending > 0 && <span className="badge-count">{pending}</span>}</NavLink>
          <NavLink to="/labeling">Labeling</NavLink>
          <NavLink to="/dashboard">Bias-Dashboard</NavLink>
          <NavLink to="/settings">Einstellungen</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/queue" element={<AgentQueue />} />
          <Route path="/labeling" element={<Labeling />} />
          <Route path="/dashboard" element={<Navigate to="/dashboard/problem" replace />} />
          <Route path="/dashboard/:phase" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
