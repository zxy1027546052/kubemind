import { useEffect, useState } from 'react';
import PageErrorBoundary from '../components/PageErrorBoundary';
import {
  api,
  type AuditRecordResponse,
  type MCPServer,
  type MCPServerCreate,
  type MCPServerUpdate,
  type SecurityPolicy,
  type Tool,
  type ToolExecuteRequest,
  type ToolExecuteResponse,
} from '../services/api';

const TABS = [
  { key: 'servers', label: 'MCP Server' },
  { key: 'tools', label: 'Tool Registry' },
  { key: 'audit', label: 'Audit Log' },
  { key: 'policies', label: 'Policies' },
];

export default function MCP() {
  return (
    <PageErrorBoundary title="MCP 加载失败">
      <MCPInner />
    </PageErrorBoundary>
  );
}

function MCPInner() {
  const [activeTab, setActiveTab] = useState('servers');
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [auditRecords, setAuditRecords] = useState<AuditRecordResponse[]>([]);
  const [policies, setPolicies] = useState<SecurityPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [toolParams, setToolParams] = useState('{}');
  const [executeResult, setExecuteResult] = useState<ToolExecuteResponse | null>(null);
  const [notice, setNotice] = useState<string>('');
  const [serverForm, setServerForm] = useState<MCPServerCreate & { id?: number }>({
    id: undefined,
    name: '',
    type: 'local',
    endpoint: '',
    metadata_json: '{}',
  });

  useEffect(() => {
    void loadData();
  }, [activeTab]);

  async function loadData() {
    setLoading(true);
    setNotice('');
    try {
      if (activeTab === 'servers') setServers((await api.listMCPServers()).items);
      if (activeTab === 'tools') setTools((await api.listTools()).items);
      if (activeTab === 'audit') setAuditRecords((await api.listAuditRecords()).items);
      if (activeTab === 'policies') setPolicies((await api.listPolicies()).items);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Load failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleExecuteTool() {
    if (!selectedTool) return;
    try {
      const params = toolParams.trim() ? JSON.parse(toolParams) : {};
      const request: ToolExecuteRequest = {
        tool_name: selectedTool.name,
        params,
        namespace: typeof params.namespace === 'string' ? params.namespace : '',
      };
      const result = await api.executeTool(request);
      setExecuteResult(result);
    } catch (err) {
      setExecuteResult({
        success: false,
        error: err instanceof Error ? err.message : 'Execution failed',
        duration_ms: 0,
      });
    }
  }

  async function handleSaveServer() {
    try {
      const data: MCPServerCreate | MCPServerUpdate = {
        name: serverForm.name,
        type: serverForm.type,
        endpoint: serverForm.endpoint,
        metadata_json: serverForm.metadata_json,
      };
      if (selectedServer) await api.updateMCPServer(selectedServer.id, data as Partial<MCPServer>);
      else await api.createMCPServer(data as Partial<MCPServer>);
      setShowModal(null);
      resetServerForm();
      await loadData();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : 'Save failed');
    }
  }

  async function handleDeleteServer(id: number) {
    if (!confirm('Delete this MCP server?')) return;
    await api.deleteMCPServer(id);
    await loadData();
  }

  async function handleTestServer(server: MCPServer) {
    try {
      const result = await api.testMCPServer(server.endpoint);
      const timeInfo = result.response_time_ms ? ` (${result.response_time_ms}ms)` : '';
      setNotice(`${server.name}: ${result.message}${timeInfo}`);
    } catch (err) {
      setNotice(`${server.name}: ${err instanceof Error ? err.message : 'connection failed'}`);
    }
  }

  function openCreateModal() {
    resetServerForm();
    setShowModal('server');
  }

  function openEditModal(server: MCPServer) {
    setSelectedServer(server);
    setServerForm({
      id: server.id,
      name: server.name,
      type: server.type,
      endpoint: server.endpoint,
      metadata_json: '{}',
    });
    setShowModal('server');
  }

  function resetServerForm() {
    setServerForm({ id: undefined, name: '', type: 'local', endpoint: '', metadata_json: '{}' });
    setSelectedServer(null);
  }

  function openExecuteModal(tool: Tool) {
    setSelectedTool(tool);
    setExecuteResult(null);
    setToolParams(exampleParams(tool));
    setShowModal('execute');
  }

  function exampleParams(tool: Tool) {
    if (tool.name === 'k8s_get_pods') return '{"namespace":"default"}';
    if (tool.name === 'k8s_describe_pod') return '{"namespace":"default","name":"example-pod"}';
    if (tool.name === 'k8s_get_pod_logs') return '{"namespace":"default","name":"example-pod","tail_lines":50}';
    if (tool.name === 'prometheus_query') return '{"query":"up"}';
    if (tool.name === 'prometheus_range_query') return '{"query":"up","start":"2026-05-16T00:00:00+00:00","end":"2026-05-16T00:05:00+00:00","step":"30s"}';
    if (tool.name === 'loki_query') return '{"query":"{namespace=\\"default\\"}","start":"2026-05-16T00:00:00+00:00","end":"2026-05-16T00:05:00+00:00","limit":20}';
    return '{}';
  }

  function renderServers() {
    return (
      <div>
        <div className="toolbar">
          <button className="primary" onClick={openCreateModal}>+ Add Server</button>
          <button onClick={loadData}>Refresh</button>
          <div className="spacer" />
          <span className="mcp-count">Total {servers.length} servers</span>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th><th>Name</th><th>Type</th><th>Status</th><th>Endpoint</th><th>Tools</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {servers.map((server) => (
                <tr key={server.id}>
                  <td>{server.id}</td>
                  <td>{server.name}</td>
                  <td>{server.type}</td>
                  <td>{server.status}</td>
                  <td className="col-mono">{server.endpoint}</td>
                  <td>{server.tools_count}</td>
                  <td className="table-actions">
                    <button className="small mcp-action" onClick={() => handleTestServer(server)}>TEST</button>
                    <button className="small mcp-action" onClick={() => openEditModal(server)}>EDIT</button>
                    <button className="danger small" onClick={() => handleDeleteServer(server.id)}>DEL</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function renderTools() {
    const categories = [...new Set(tools.map((tool) => tool.category))];
    return (
      <div className="mcp-tool-list">
        {categories.map((category) => (
          <section key={category} className="mcp-tool-section">
            <div className="mcp-section-header">
              <h3>{category}</h3>
              <span>{tools.filter((tool) => tool.category === category).length} tools</span>
            </div>
            <div className="mcp-tools-grid">
              {tools.filter((tool) => tool.category === category).map((tool) => (
                <div key={tool.id} className="mcp-tool-card">
                  <div className="mcp-tool-card-header">
                    <span className="mcp-tool-name">{tool.name}</span>
                    <span className={`tag ${tool.risk_level === 'low' ? 'tag-runbook' : 'tag-doc'}`}>{tool.risk_level}</span>
                  </div>
                  <p>{tool.description}</p>
                  <div className="mcp-tool-meta">
                    <span>{tool.timeout_ms}ms</span>
                    <span>retry {tool.retry}</span>
                    <span>{tool.enabled ? 'enabled' : 'disabled'}</span>
                  </div>
                  <button className="primary small" onClick={() => openExecuteModal(tool)}>EXECUTE</button>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    );
  }

  function renderAudit() {
    return (
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th><th>Tool</th><th>Category</th><th>Status</th><th>Duration</th><th>Namespace</th><th>Time</th>
            </tr>
          </thead>
          <tbody>
            {auditRecords.map((record) => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>{record.tool_name}</td>
                <td>{record.category}</td>
                <td><span className={`status-badge status-${record.status.toLowerCase()}`}>{record.status}</span></td>
                <td>{record.duration_ms}ms</td>
                <td>{record.namespace || '-'}</td>
                <td>{new Date(record.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function renderPolicies() {
    return (
      <div className="mcp-policies-grid">
        {policies.map((policy) => (
          <div key={policy.id} className="mcp-policy-card">
            <div className="mcp-policy-card-header">
              <span>{policy.name}</span>
              <span className={`tag ${policy.enabled ? 'tag-runbook' : 'tag-case'}`}>
                {policy.enabled ? 'enabled' : 'disabled'}
              </span>
            </div>
            <div className="mcp-policy-type">{policy.type}</div>
            <p>{policy.description}</p>
            <pre>{policy.rules}</pre>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="mcp-page">
      <header className="page-header stagger-1">
        <div className="page-eyebrow">mcp_ops_tools</div>
        <h1>MCP Ops Tools</h1>
        <p className="subtitle">FastMCP microservice · tool registry · policy checks · audit trail</p>
      </header>
      {notice && <div className="chatops-error">{notice}</div>}
      <div className="card stagger-2">
        <div className="tabs">
          {TABS.map((tab) => (
            <button key={tab.key} className={`tab ${activeTab === tab.key ? 'active' : ''}`} onClick={() => setActiveTab(tab.key)}>
              {tab.label}
            </button>
          ))}
        </div>
        {loading ? <div className="loading-spinner"><div className="spinner" /><span>Loading...</span></div> : (
          <>
            {activeTab === 'servers' && renderServers()}
            {activeTab === 'tools' && renderTools()}
            {activeTab === 'audit' && renderAudit()}
            {activeTab === 'policies' && renderPolicies()}
          </>
        )}
      </div>

      {showModal === 'server' && (
        <div className="modal-overlay" onClick={() => setShowModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedServer ? 'Edit MCP Server' : 'Add MCP Server'}</h3>
              <button className="modal-close" onClick={() => setShowModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-group"><label>Name</label><input value={serverForm.name} onChange={(e) => setServerForm({ ...serverForm, name: e.target.value })} /></div>
              <div className="form-group"><label>Type</label><select value={serverForm.type} onChange={(e) => setServerForm({ ...serverForm, type: e.target.value })}><option value="local">local</option><option value="remote">remote</option></select></div>
              <div className="form-group"><label>Endpoint</label><input value={serverForm.endpoint} onChange={(e) => setServerForm({ ...serverForm, endpoint: e.target.value })} placeholder="http://127.0.0.1:11000/mcp/" /></div>
              <div className="form-group"><label>Metadata JSON</label><textarea className="code-textarea" value={serverForm.metadata_json} onChange={(e) => setServerForm({ ...serverForm, metadata_json: e.target.value })} /></div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowModal(null)}>Cancel</button>
              <button className="primary" onClick={handleSaveServer}>Save</button>
            </div>
          </div>
        </div>
      )}

      {showModal === 'execute' && selectedTool && (
        <div className="modal-overlay" onClick={() => setShowModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Execute: {selectedTool.name}</h3>
              <button className="modal-close" onClick={() => setShowModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-group"><label>Parameters JSON</label><textarea className="code-textarea" rows={8} value={toolParams} onChange={(e) => setToolParams(e.target.value)} /></div>
              <div className="form-group"><label>Schema</label><div className="code-block"><pre>{selectedTool.parameters}</pre></div></div>
              {executeResult && <div className="form-group"><label>Result</label><div className="code-block"><pre>{JSON.stringify(executeResult, null, 2)}</pre></div></div>}
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowModal(null)}>Close</button>
              <button className="primary" onClick={handleExecuteTool}>Execute</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
