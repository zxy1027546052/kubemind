import { useState, useEffect, useCallback } from 'react';
import { api, type DiagnosisResponse } from '../services/api';

export default function Diagnosis() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  const [history, setHistory] = useState<DiagnosisResponse[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchHistory = useCallback(async () => {
    try {
      const data = await api.listDiagnoses({ limit: 10 });
      setHistory(data);
    } catch {
      // History load failed silently
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  async function handleSubmit() {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await api.createDiagnosis({ query_text: query.trim() });
      setResult(data);
      fetchHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : '诊断失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleViewHistory(id: number) {
    setLoading(true);
    setError('');
    try {
      const data = await api.getDiagnosis(id);
      setResult(data);
      setQuery(data.query_text);
    } catch {
      setError('加载诊断记录失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteHistory(id: number) {
    try {
      await api.deleteDiagnosis(id);
      fetchHistory();
      if (result?.id === id) setResult(null);
    } catch {
      // Ignore
    }
  }

  function formatDate(iso: string): string {
    try {
      const d = new Date(iso);
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    } catch {
      return iso;
    }
  }

  // Show no history state only when not submitting and not viewing a result
  const showPlaceholder = !loading && !result && history.length === 0 && !historyLoading && !error;

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">intelligent_diagnosis</div>
        <h1>智能诊断</h1>
        <p className="subtitle">AI 驱动的故障根因分析与诊断建议</p>
      </header>

      <div className="card stagger-2" style={{ marginBottom: '24px' }}>
        <div style={{ padding: '24px' }}>
          <label
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--accent-cyan)',
              display: 'block',
              marginBottom: '12px',
            }}
          >
            {'>'} describe_fault
          </label>
          <textarea
            placeholder="描述你遇到的故障现象，例如: 生产环境 MySQL 大量连接超时，API 返回 connect timeout..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.ctrlKey) handleSubmit();
            }}
            rows={4}
            style={{
              width: '100%',
              background: 'var(--bg-root)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-body)',
              fontSize: '0.875rem',
              padding: '16px',
              resize: 'vertical',
              borderRadius: '4px',
            }}
          />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '16px',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.625rem',
                color: 'var(--text-muted)',
              }}
            >
              Ctrl + Enter to submit
            </span>
            <button
              className="primary"
              onClick={handleSubmit}
              disabled={loading || !query.trim()}
              style={{ minWidth: '140px', textAlign: 'center' }}
            >
              {loading ? '分析中...' : '开始诊断'}
            </button>
          </div>
          {error && (
            <div
              style={{
                marginTop: '12px',
                padding: '8px 16px',
                borderLeft: '3px solid var(--accent-red)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                color: 'var(--accent-red)',
              }}
            >
              ERR: {error}
            </div>
          )}
        </div>
      </div>

      {/* Placeholder */}
      {showPlaceholder && (
        <div className="placeholder-page stagger-3">
          <div className="ph-icon">{'{ -_- }'}</div>
          <h2>诊断引擎就绪</h2>
          <p>输入故障描述后开始智能诊断。基于知识库中的案例和 Runbook 进行 RAG 检索与根因分析。</p>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: '85%', marginLeft: 0, animation: 'none' }}
            />
          </div>
        </div>
      )}

      {/* Diagnosis Result */}
      {result && (
        <div className="card stagger-3" style={{ marginBottom: '24px' }}>
          <div style={{ padding: '24px' }}>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                color: 'var(--accent-cyan)',
                marginBottom: '16px',
              }}
            >
              {'>'} diagnosis_report :: session_{result.id} :: {result.status}
            </div>

            {/* Root Causes */}
            <div style={{ marginBottom: '20px' }}>
              <h3
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '0.875rem',
                  color: 'var(--accent-red)',
                  marginBottom: '12px',
                }}
              >
                ▋ 根因候选
              </h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {result.llm_response.root_causes.map((rc, i) => (
                  <li
                    key={i}
                    style={{
                      fontFamily: 'var(--font-body)',
                      fontSize: '0.8125rem',
                      color: 'var(--text-primary)',
                      padding: '8px 12px',
                      background: 'var(--bg-root)',
                      borderLeft: '2px solid var(--accent-red)',
                      marginBottom: '6px',
                      borderRadius: '0 4px 4px 0',
                    }}
                  >
                    {rc}
                  </li>
                ))}
              </ul>
            </div>

            {/* Steps */}
            <div style={{ marginBottom: '20px' }}>
              <h3
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '0.875rem',
                  color: 'var(--accent-cyan)',
                  marginBottom: '12px',
                }}
              >
                ▋ 排查步骤
              </h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {result.llm_response.steps.map((step, i) => (
                  <li
                    key={i}
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      padding: '6px 0',
                    }}
                  >
                    {step}
                  </li>
                ))}
              </ul>
            </div>

            {/* Impact */}
            {result.llm_response.impact && (
              <div style={{ marginBottom: '20px' }}>
                <h3
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '0.875rem',
                    color: 'var(--accent-amber)',
                    marginBottom: '8px',
                  }}
                >
                  ▋ 影响评估
                </h3>
                <p
                  style={{
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.8125rem',
                    color: 'var(--text-secondary)',
                    padding: '8px 12px',
                    background: 'var(--bg-root)',
                    borderRadius: '4px',
                  }}
                >
                  {result.llm_response.impact}
                </p>
              </div>
            )}

            {/* Runbook Refs */}
            {result.llm_response.runbook_refs.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '0.875rem',
                    color: 'var(--accent-green)',
                    marginBottom: '12px',
                  }}
                >
                  ▋ 建议 Runbook
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {result.llm_response.runbook_refs.map((rb, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '8px 12px',
                        background: 'var(--bg-root)',
                        borderRadius: '4px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.75rem',
                      }}
                    >
                      <span style={{ color: 'var(--text-primary)' }}>{rb.title}</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        {Math.round((rb.score || 0) * 100)}% match
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Matched Items */}
            {result.matched_items.length > 0 && (
              <div>
                <h3
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                    marginBottom: '8px',
                  }}
                >
                  ▋ 匹配的知识条目
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {result.matched_items.map((item, i) => (
                    <span
                      key={i}
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.625rem',
                        padding: '2px 8px',
                        background: 'var(--bg-root)',
                        border: '1px solid var(--border-default)',
                        borderRadius: '3px',
                        color: 'var(--text-muted)',
                      }}
                    >
                      [{item.source_type}] {item.title.slice(0, 30)}... (
                      {Math.round(item.score * 100)}%)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* History */}
      {!historyLoading && history.length > 0 && (
        <div className="card stagger-3">
          <div style={{ padding: '20px 24px' }}>
            <h3
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                marginBottom: '12px',
              }}
            >
              ▋ 诊断历史
            </h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>查询内容</th>
                  <th>状态</th>
                  <th>时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id}>
                    <td className="col-title" style={{ maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {h.query_text}
                    </td>
                    <td>
                      <span className={`tag ${h.status === 'completed' ? 'tag-runbook' : 'tag-doc'}`}>
                        {h.status}
                      </span>
                    </td>
                    <td className="col-mono">{formatDate(h.created_at)}</td>
                    <td>
                      <button
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.6875rem',
                          padding: '4px 12px',
                          background: 'transparent',
                          border: '1px solid var(--border-default)',
                          color: 'var(--accent-cyan)',
                          cursor: 'pointer',
                          borderRadius: '4px',
                          marginRight: '6px',
                        }}
                        onClick={() => handleViewHistory(h.id)}
                      >
                        查看
                      </button>
                      <button
                        className="danger"
                        onClick={() => handleDeleteHistory(h.id)}
                        style={{ padding: '4px 8px', fontSize: '0.625rem' }}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
