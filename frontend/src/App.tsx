import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import KnowledgeCenter from './pages/KnowledgeCenter';
import Dashboard from './pages/Dashboard';
import Clusters from './pages/Clusters';
import Topology from './pages/Topology';
import Alerts from './pages/Alerts';
import Diagnosis from './pages/Diagnosis';
import ChatOps from './pages/ChatOps';
import Workflows from './pages/Workflows';
import Models from './pages/Models';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/knowledge" replace />} />
          <Route path="knowledge" element={<KnowledgeCenter />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="clusters" element={<Clusters />} />
          <Route path="topology" element={<Topology />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="diagnosis" element={<Diagnosis />} />
          <Route path="chatops" element={<ChatOps />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="models" element={<Models />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
