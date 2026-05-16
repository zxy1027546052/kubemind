import { useState, useEffect, useCallback } from 'react';
import { api, type WorkflowResponse, type WorkflowStep } from '../services/api';
import PageErrorBoundary from '../components/PageErrorBoundary';

const STATUS_OPTIONS = [
  { value: '', label: '所有状态' },
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
];

function getStatusClass(status: string): string {
  if (status === 'active') return 'tag-runbook';
  if (status === 'draft') return 'tag-doc';
  if (status === 'archived') return '';
  return '';
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

function parseSteps(stepsJson: string): WorkflowStep[] {
  try {
    return JSON.parse(stepsJson);
  } catch {
    return [];
  }
}

export default function Workflows() {
  return (
    <PageErrorBoundary title="工作流加载失败">
      <WorkflowsInner />
    </PageErrorBoundary>
  );
}

function WorkflowsInner() {
  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listWorkflows({
        status: statusFilter || undefined,
        limit: 50,
      });
      setWorkflows(data.items);
      setTotal(data.pagination.total);
    } catch {
      setWorkflows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">workflow_engine</div>
        <h1>工作流</h1>
        <p className="subtitle">可编排的自动化运维流程引擎</p>
      </header>

      <div className="card stagger-2">
        {/* Filters */}
        <div className="toolbar stagger-3">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <div className="spacer" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            共 {total} 条流程
          </span>
        </div>

        {/* Table */}
        <table className="data-table">
          <thead>
            <tr>
              <th>流程名称</th>
              <th>分类</th>
              <th>步骤数</th>
              <th>状态</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '40px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    加载中<span style={{ animation: 'cursor-blink 1s step-end infinite' }}>_</span>
                  </span>
                </td>
              </tr>
            ) : workflows.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="empty-state">
                    <div className="empty-icon">{'[O  O  O]'}</div>
                    <h3>暂无工作流</h3>
                    <p>创建标准化的故障处理流程模板</p>
                  </div>
                </td>
              </tr>
            ) : (
              workflows.map((wf, i) => {
                const steps = parseSteps(wf.steps);
                return (
                  <>
                    <tr
                      key={wf.id}
                      className={`stagger-${Math.min(i + 3, 6)}`}
                      onClick={() => setExpandedId(expandedId === wf.id ? null : wf.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className="col-title">{wf.title}</td>
                      <td className="col-mono">{wf.category || '-'}</td>
                      <td className="col-mono">{steps.length} 步</td>
                      <td><span className={`tag ${getStatusClass(wf.status)}`}>{wf.status}</span></td>
                      <td className="col-mono">{formatDate(wf.updated_at)}</td>
                    </tr>
                    {expandedId === wf.id && (
                      <tr key={`${wf.id}-detail`}>
                        <td colSpan={5} style={{ padding: '16px 24px', background: 'var(--bg-root)' }}>
                          {wf.description && (
                            <p style={{ fontFamily: 'var(--font-body)', fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                              {wf.description}
                            </p>
                          )}
                          {steps.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                              {steps.map((step, si) => (
                                <div key={si} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '8px 0', borderBottom: si < steps.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                                  <div style={{
                                    minWidth: '28px',
                                    height: '28px',
                                    borderRadius: '50%',
                                    background: 'var(--accent-cyan)',
                                    color: 'var(--bg-root)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontFamily: 'var(--font-mono)',
                                    fontSize: '0.6875rem',
                                    fontWeight: 700,
                                    flexShrink: 0,
                                  }}>
                                    {step.order}
                                  </div>
                                  <div>
                                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.8125rem', color: 'var(--text-primary)', marginBottom: '4px' }}>
                                      {step.action}
                                    </div>
                                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                                      {step.detail}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
