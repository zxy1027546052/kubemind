import { useState, useEffect, useCallback } from 'react';
import { api, type ModelConfigResponse, type ModelConfigCreate } from '../services/api';
import PageErrorBoundary from '../components/PageErrorBoundary';

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch { return iso; }
}

export default function Models() {
  return (
    <PageErrorBoundary title="模型配置加载失败">
      <ModelsInner />
    </PageErrorBoundary>
  );
}

function ModelsInner() {
  const [models, setModels] = useState<ModelConfigResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; success: boolean; message: string } | null>(null);
  const [form, setForm] = useState<ModelConfigCreate>({
    name: '', provider: 'deepseek', model_type: 'llm', endpoint: '', api_key: '', model_name: '', config_json: '{}',
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listModels({ limit: 50 });
      setModels(data.items);
    } catch { setModels([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchModels(); }, [fetchModels]);

  function openCreate() {
    setEditingId(null);
    setForm({ name: '', provider: 'deepseek', model_type: 'llm', endpoint: '', api_key: '', model_name: '', config_json: '{}' });
    setShowModal(true);
  }

  function openEdit(m: ModelConfigResponse) {
    setEditingId(m.id);
    setForm({ name: m.name, provider: m.provider, model_type: m.model_type, endpoint: m.endpoint, api_key: '', model_name: m.model_name, config_json: m.config_json });
    setShowModal(true);
  }

  async function handleSubmit() {
    if (!form.name.trim() || !form.endpoint.trim() || !form.model_name.trim()) return;
    setSubmitting(true);
    try {
      if (editingId) {
        const payload: any = { ...form };
        if (!payload.api_key) delete payload.api_key;
        await api.updateModel(editingId, payload);
      } else {
        await api.createModel(form);
      }
      setShowModal(false);
      fetchModels();
    } catch { /* ignore */ }
    finally { setSubmitting(false); }
  }

  async function handleDelete(id: number) {
    try { await api.deleteModel(id); fetchModels(); } catch { /* ignore */ }
  }

  async function handleTest(id: number) {
    setTestingId(id);
    setTestResult(null);
    try {
      const res = await api.testModelConnection(id);
      setTestResult({ id, success: res.success, message: res.message });
    } catch {
      setTestResult({ id, success: false, message: 'Network error' });
    } finally { setTestingId(null); }
  }

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">ai_model_config</div>
        <h1>AI 模型</h1>
        <p className="subtitle">LLM · Embedding · 向量数据库 · RAG 检索配置</p>
      </header>

      <div className="card stagger-2">
        <div className="toolbar stagger-3">
          <button className="primary" onClick={openCreate}>+ 添加配置</button>
          <div className="spacer" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            共 {models.length} 条配置
          </span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>提供商</th>
              <th>类型</th>
              <th>模型</th>
              <th>状态</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: '40px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  加载中<span style={{ animation: 'cursor-blink 1s step-end infinite' }}>_</span>
                </span>
              </td></tr>
            ) : models.length === 0 ? (
              <tr><td colSpan={7}>
                <div className="empty-state">
                  <div className="empty-icon">[AI]</div>
                  <h3>暂无模型配置</h3>
                  <p>添加 LLM 或 Embedding 模型配置以启用 AI 能力</p>
                </div>
              </td></tr>
            ) : models.map((m, i) => (
              <tr key={m.id} className={`stagger-${Math.min(i + 3, 6)}`}>
                <td className="col-title">{m.name}</td>
                <td className="col-mono">{m.provider}</td>
                <td><span className={`tag ${m.model_type === 'llm' ? 'tag-runbook' : 'tag-case'}`}>{m.model_type}</span></td>
                <td className="col-mono">{m.model_name}</td>
                <td>
                  <span className={`status-dot ${m.is_active ? '' : 'offline'}`}
                    style={{ display: 'inline-block', marginRight: '6px' }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: m.is_active ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                    {m.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </td>
                <td className="col-mono">{formatDate(m.updated_at)}</td>
                <td>
                  <button style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', padding: '3px 8px', background: 'transparent', border: '1px solid var(--accent-cyan)', color: 'var(--accent-cyan)', cursor: 'pointer', borderRadius: '3px', marginRight: '4px' }}
                    onClick={() => handleTest(m.id)} disabled={testingId === m.id}>
                    {testingId === m.id ? '...' : 'TEST'}
                  </button>
                  <button style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', padding: '3px 8px', background: 'transparent', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', cursor: 'pointer', borderRadius: '3px', marginRight: '4px' }}
                    onClick={() => openEdit(m)}>EDIT</button>
                  <button className="danger" onClick={() => handleDelete(m.id)} style={{ padding: '3px 8px', fontSize: '0.625rem' }}>DEL</button>
                  {testResult?.id === m.id && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', marginLeft: '6px', color: testResult.success ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                      {testResult.success ? 'OK' : 'FAIL'}: {testResult.message.slice(0, 40)}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '560px' }}>
            <div className="modal-header">
              <h2>{editingId ? '编辑配置' : '添加模型配置'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>x</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>名称 *</label>
                <input placeholder="例如: DeepSeek Chat (生产)" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label>提供商</label>
                  <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}>
                    <option value="deepseek">DeepSeek</option>
                    <option value="openai">OpenAI</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>类型</label>
                  <select value={form.model_type} onChange={(e) => setForm({ ...form, model_type: e.target.value })}>
                    <option value="llm">LLM</option>
                    <option value="embedding">Embedding</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Endpoint *</label>
                <input placeholder="https://api.deepseek.com/v1" value={form.endpoint}
                  onChange={(e) => setForm({ ...form, endpoint: e.target.value })} />
              </div>
              <div className="form-group">
                <label>API Key {editingId ? '(留空不修改)' : '*'}</label>
                <input type="password" placeholder="sk-..." value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
              </div>
              <div className="form-group">
                <label>模型名称 *</label>
                <input placeholder="deepseek-chat" value={form.model_name}
                  onChange={(e) => setForm({ ...form, model_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>配置 JSON</label>
                <textarea rows={3} placeholder='{"temperature": 0.7, "max_tokens": 4096}' value={form.config_json}
                  onChange={(e) => setForm({ ...form, config_json: e.target.value })} />
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowModal(false)}>取消</button>
              <button className="primary" onClick={handleSubmit} disabled={submitting}>
                {submitting ? '提交中...' : editingId ? '保存修改' : '确认添加'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
