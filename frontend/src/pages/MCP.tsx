import { useState, useEffect } from 'react';
import { api, type MCPServer, type Tool, type AuditRecordResponse, type SecurityPolicy, type ToolExecuteRequest, type MCPServerCreate, type MCPServerUpdate } from '../services/api';

const TABS = [
  { key: 'servers', label: 'MCP Server' },
  { key: 'tools', label: '工具注册表' },
  { key: 'audit', label: '审计记录' },
  { key: 'policies', label: '安全策略' },
];

export default function MCP() {
  const [activeTab, setActiveTab] = useState('servers');
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [auditRecords, setAuditRecords] = useState<AuditRecordResponse[]>([]);
  const [policies, setPolicies] = useState<SecurityPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [toolParams, setToolParams] = useState<string>('');
  const [executeResult, setExecuteResult] = useState<any>(null);
  
  // 服务器表单状态
  const [serverForm, setServerForm] = useState<MCPServerCreate & { id?: number }>({
    id: undefined,
    name: '',
    type: 'local',
    endpoint: '',
    metadata_json: '{}',
  });

  useEffect(() => {
    loadData();
  }, [activeTab]);

  async function loadData() {
    setLoading(true);
    try {
      if (activeTab === 'servers') {
        const res = await api.listMCPServers();
        setServers(res.items);
      } else if (activeTab === 'tools') {
        const res = await api.listTools();
        setTools(res.items);
      } else if (activeTab === 'audit') {
        const res = await api.listAuditRecords();
        setAuditRecords(res.items);
      } else if (activeTab === 'policies') {
        const res = await api.listPolicies();
        setPolicies(res.items);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleExecuteTool() {
    if (!selectedTool) return;
    try {
      let params = {};
      if (toolParams.trim()) {
        params = JSON.parse(toolParams);
      }
      const request: ToolExecuteRequest = {
        tool_name: selectedTool.name,
        params,
      };
      const result = await api.executeTool(request);
      setExecuteResult(result);
    } catch (err) {
      console.error(err);
      setExecuteResult({ success: false, error: err instanceof Error ? err.message : 'Unknown error' });
    }
  }

  // 服务器操作
  async function handleCreateServer() {
    try {
      const data: MCPServerCreate = {
        name: serverForm.name,
        type: serverForm.type,
        endpoint: serverForm.endpoint,
        metadata_json: serverForm.metadata_json,
      };
      await api.createMCPServer(data);
      setShowModal(null);
      resetServerForm();
      await loadData();
    } catch (err) {
      console.error(err);
    }
  }

  async function handleUpdateServer() {
    if (!selectedServer) return;
    try {
      const data: MCPServerUpdate = {
        name: serverForm.name,
        type: serverForm.type,
        endpoint: serverForm.endpoint,
        metadata_json: serverForm.metadata_json,
      };
      await api.updateMCPServer(selectedServer.id, data);
      setShowModal(null);
      resetServerForm();
      await loadData();
    } catch (err) {
      console.error(err);
    }
  }

  async function handleDeleteServer(id: number) {
    if (!confirm('确定要删除这个 MCP Server 吗？')) return;
    try {
      await api.deleteMCPServer(id);
      await loadData();
    } catch (err) {
      console.error(err);
    }
  }

  function openCreateModal() {
    resetServerForm();
    setShowModal('create-server');
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
    setShowModal('edit-server');
  }

  function resetServerForm() {
    setServerForm({
      id: undefined,
      name: '',
      type: 'local',
      endpoint: '',
      metadata_json: '{}',
    });
    setSelectedServer(null);
  }

  function getRiskColor(risk: string) {
    switch (risk) {
      case 'critical': return '#f85149';
      case 'high': return '#d29922';
      case 'medium': return '#58a6ff';
      case 'low': return '#3fb950';
      default: return '#6e7681';
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'online': return '#3fb950';
      case 'offline': return '#8b949e';
      case 'error': return '#f85149';
      default: return '#6e7681';
    }
  }

  function renderServers() {
    return (
      <div>
        <div className="toolbar">
          <button className="btn btn-primary" onClick={openCreateModal}>
            + 添加服务器
          </button>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>名称</th>
                <th>类型</th>
                <th>状态</th>
                <th>端点</th>
                <th>工具数</th>
                <th>最后心跳</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {servers.map((server) => (
                <tr key={server.id}>
                  <td>{server.id}</td>
                  <td>{server.name}</td>
                  <td>{server.type}</td>
                  <td>
                    <span className="status-dot" style={{ backgroundColor: getStatusColor(server.status), boxShadow: `0 0 8px ${getStatusColor(server.status)}` }} />
                    {server.status.toUpperCase()}
                  </td>
                  <td>{server.endpoint}</td>
                  <td>{server.tools_count}</td>
                  <td>{server.last_heartbeat || '-'}</td>
                  <td className="table-actions">
                    <button className="btn btn-sm btn-primary" onClick={() => openEditModal(server)}>编辑</button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDeleteServer(server.id)}>删除</button>
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
    const categories = [...new Set(tools.map(t => t.category))];
    return (
      <div>
        {categories.map(category => (
          <div key={category} className="tool-category-section">
            <h3 className="tool-category-title">{category}</h3>
            <div className="tools-grid">
              {tools.filter(t => t.category === category).map(tool => (
                <div key={tool.id} className="tool-card">
                  <div className="tool-card-header">
                    <span className="tool-card-name">{tool.name}</span>
                    <span className="tool-card-risk" style={{ backgroundColor: getRiskColor(tool.risk_level) }}>
                      {tool.risk_level.toUpperCase()}
                    </span>
                  </div>
                  <div className="tool-card-description">{tool.description}</div>
                  <div className="tool-card-meta">
                    <span>超时: {tool.timeout_ms}ms</span>
                    <span>重试: {tool.retry}次</span>
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={() => { setSelectedTool(tool); setShowModal('execute'); }}>
                    执行
                  </button>
                </div>
              ))}
            </div>
          </div>
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
              <th>ID</th>
              <th>工具</th>
              <th>分类</th>
              <th>调用者</th>
              <th>会话</th>
              <th>状态</th>
              <th>耗时</th>
              <th>命名空间</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {auditRecords.map((record) => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>{record.tool_name}</td>
                <td>{record.category}</td>
                <td>{record.caller}</td>
                <td>{record.session_id || '-'}</td>
                <td><span className={`status-badge status-${record.status.toLowerCase()}`}>{record.status.toUpperCase()}</span></td>
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
      <div className="policies-grid">
        {policies.map(policy => (
          <div key={policy.id} className="policy-card">
            <div className="policy-card-header">
              <span className="policy-card-name">{policy.name}</span>
              <span className={`policy-card-status ${policy.enabled ? 'enabled' : 'disabled'}`}>
                {policy.enabled ? '已启用' : '已禁用'}
              </span>
            </div>
            <div className="policy-card-type">{policy.type}</div>
            <div className="policy-card-description">{policy.description}</div>
            <div className="policy-card-rules">
              <code>{policy.rules}</code>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="page-container mcp-page scan-lines">
      <div className="page-header">
        <h1 className="page-title">MCP 运维工具</h1>
        <p className="page-subtitle">管理 MCP Server、工具注册、权限校验和审计记录</p>
      </div>

      <div className="tabs-container">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="content-card">
        {loading ? (
          <div className="loading-spinner">
            <div className="spinner" />
            <span>加载中...</span>
          </div>
        ) : (
          <>
            {activeTab === 'servers' && renderServers()}
            {activeTab === 'tools' && renderTools()}
            {activeTab === 'audit' && renderAudit()}
            {activeTab === 'policies' && renderPolicies()}
          </>
        )}
      </div>

      {/* 创建/编辑服务器模态框 */}
      {(showModal === 'create-server' || showModal === 'edit-server') && (
        <div className="modal-overlay" onClick={() => setShowModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{showModal === 'create-server' ? '添加 MCP Server' : '编辑 MCP Server'}</h3>
              <button className="modal-close" onClick={() => setShowModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>名称 *</label>
                <input
                  type="text"
                  value={serverForm.name}
                  onChange={(e) => setServerForm({ ...serverForm, name: e.target.value })}
                  placeholder="输入服务器名称"
                  required
                />
              </div>
              <div className="form-group">
                <label>类型</label>
                <select
                  value={serverForm.type}
                  onChange={(e) => setServerForm({ ...serverForm, type: e.target.value })}
                >
                  <option value="local">本地</option>
                  <option value="remote">远程</option>
                </select>
              </div>
              <div className="form-group">
                <label>端点 *</label>
                <input
                  type="text"
                  value={serverForm.endpoint}
                  onChange={(e) => setServerForm({ ...serverForm, endpoint: e.target.value })}
                  placeholder="http://localhost:8080"
                  required
                />
              </div>
              <div className="form-group">
                <label>元数据 (JSON)</label>
                <textarea
                  className="code-textarea"
                  rows={4}
                  value={serverForm.metadata_json}
                  onChange={(e) => setServerForm({ ...serverForm, metadata_json: e.target.value })}
                  placeholder='{"key": "value"}'
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(null)}>取消</button>
              <button className="btn btn-primary" onClick={showModal === 'create-server' ? handleCreateServer : handleUpdateServer}>
                {showModal === 'create-server' ? '创建' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 执行工具模态框 */}
      {showModal === 'execute' && selectedTool && (
        <div className="modal-overlay" onClick={() => setShowModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>执行工具: {selectedTool.name}</h3>
              <button className="modal-close" onClick={() => setShowModal(null)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>参数 (JSON 格式)</label>
                <textarea
                  className="code-textarea"
                  rows={8}
                  value={toolParams}
                  onChange={(e) => setToolParams(e.target.value)}
                  placeholder='{"namespace": "default"}'
                />
              </div>
              <div className="form-group">
                <label>工具信息</label>
                <div className="code-block">
                  <p><strong>分类:</strong> {selectedTool.category}</p>
                  <p><strong>风险等级:</strong> {selectedTool.risk_level}</p>
                  <p><strong>超时:</strong> {selectedTool.timeout_ms}ms</p>
                  <p><strong>描述:</strong> {selectedTool.description}</p>
                  <p><strong>函数名:</strong> {selectedTool.function_name}</p>
                  <p><strong>参数定义:</strong> {selectedTool.parameters}</p>
                </div>
              </div>
              {executeResult && (
                <div className="form-group">
                  <label>执行结果</label>
                  <div className="code-block">
                    <pre>{JSON.stringify(executeResult, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(null)}>关闭</button>
              <button className="btn btn-primary" onClick={handleExecuteTool}>执行</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}