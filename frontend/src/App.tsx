import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import KnowledgeCenter from './pages/KnowledgeCenter';
import Dashboard from './pages/Dashboard';
import Clusters from './pages/Clusters';
import Topology from './pages/Topology';
import Alerts from './pages/Alerts';
import ChatOps from './pages/ChatOps';
import Workflows from './pages/Workflows';
import Models from './pages/Models';
import Settings from './pages/Settings';
import MCP from './pages/MCP';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/knowledge" replace />} />
            <Route path="knowledge" element={<KnowledgeCenter />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="clusters" element={<Clusters />} />
            <Route path="topology" element={<Topology />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="diagnosis" element={<Navigate to="/chatops" replace />} />
            <Route path="chatops" element={<ChatOps />} />
            <Route path="workflows" element={<Workflows />} />
            <Route path="models" element={<Models />} />
            <Route path="settings" element={<Settings />} />
            <Route path="mcp" element={<MCP />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
