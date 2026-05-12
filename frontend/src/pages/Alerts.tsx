import { useState, useEffect, useCallback } from 'react';
import { api, type AlertResponse } from '../services/api';

const SEVERITY_OPTIONS = [
  { value: '', label: '所有等级' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const STATUS_OPTIONS = [
  { value: '', label: '所有状态' },
  { value: 'active', label: 'Active' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'resolved', label: 'Resolved' },
];

function getSeverityClass(severity: string): string {
  if (severity === 'critical') return 'tag-case';
  if (severity === 'high') return 'tag-doc';
  if (severity === 'medium') return 'tag-runbook';
  return '';
}

function getStatusClass(status: string): string {
  if (status === 'active') return 'tag-case';
  if (status === 'acknowledged') return 'tag-doc';
  if (status === 'resolved') return 'tag-runbook';
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

export default function Alerts() {
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listAlerts({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit: 50,
      });
      setAlerts(data.items);
      setTotal(data.pagination.total);
    } catch {
      setAlerts([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [severityFilter, statusFilter]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  async function handleStatusChange(id: number, newStatus: string) {
    try {
      await api.updateAlert(id, { status: newStatus });
      fetchAlerts();
    } catch {
      // Ignore
    }
  }

  async function handleDelete(id: number) {
    try {
      await api.deleteAlert(id);
      fetchAlerts();
    } catch {
      // Ignore
    }
  }

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">alert_governance</div>
        <h1>告警中心</h1>
        <p className="subtitle">告警聚合 · 降噪 · 确认 · 闭环治理</p>
      </header>

      <div className="card stagger-2">
        {/* Filters */}
        <div className="toolbar stagger-3">
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <div className="spacer" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            共 {total} 条告警
          </span>
        </div>

        {/* Table */}
        <table className="data-table">
          <thead>
            <tr>
              <th>告警标题</th>
              <th>等级</th>
              <th>来源</th>
              <th>状态</th>
              <th>负责人</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    加载中<span style={{ animation: 'cursor-blink 1s step-end infinite' }}>_</span>
                  </span>
                </td>
              </tr>
            ) : alerts.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-state">
                    <div className="empty-icon">[!!!]</div>
                    <h3>暂无告警</h3>
                    <p>Prometheus AlertManager 集成后此处将展示实时告警</p>
                  </div>
                </td>
              </tr>
            ) : (
              alerts.map((alert, i) => (
                <>
                  <tr key={alert.id} className={`stagger-${Math.min(i + 3, 6)}`} onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)} style={{ cursor: 'pointer' }}>
                    <td className="col-title">{alert.title}</td>
                    <td><span className={`tag ${getSeverityClass(alert.severity)}`}>{alert.severity}</span></td>
                    <td className="col-mono">{alert.source}</td>
                    <td><span className={`tag ${getStatusClass(alert.status)}`}>{alert.status}</span></td>
                    <td className="col-mono">{alert.assigned_to || '-'}</td>
                    <td className="col-mono">{formatDate(alert.created_at)}</td>
                    <td>
                      {alert.status !== 'resolved' && (
                        <button
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.625rem',
                            padding: '3px 8px',
                            background: 'transparent',
                            border: '1px solid var(--accent-amber)',
                            color: 'var(--accent-amber)',
                            cursor: 'pointer',
                            borderRadius: '3px',
                            marginRight: '4px',
                          }}
                          onClick={(e) => { e.stopPropagation(); handleStatusChange(alert.id, 'acknowledged'); }}
                        >
                          ACK
                        </button>
                      )}
                      {alert.status !== 'resolved' && (
                        <button
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.625rem',
                            padding: '3px 8px',
                            background: 'transparent',
                            border: '1px solid var(--accent-green)',
                            color: 'var(--accent-green)',
                            cursor: 'pointer',
                            borderRadius: '3px',
                            marginRight: '4px',
                          }}
                          onClick={(e) => { e.stopPropagation(); handleStatusChange(alert.id, 'resolved'); }}
                        >
                          RESOLVE
                        </button>
                      )}
                      <button className="danger" onClick={(e) => { e.stopPropagation(); handleDelete(alert.id); }} style={{ padding: '3px 8px', fontSize: '0.625rem' }}>
                        DEL
                      </button>
                    </td>
                  </tr>
                  {expandedId === alert.id && (
                    <tr key={`${alert.id}-detail`}>
                      <td colSpan={7} style={{ padding: '16px 24px', background: 'var(--bg-root)' }}>
                        <div style={{ fontFamily: 'var(--font-body)', fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                          {alert.description}
                        </div>
                        <div style={{ marginTop: '12px', display: 'flex', gap: '12px', fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>
                          <span>分类: {alert.category || '-'}</span>
                          <span>负责人: {alert.assigned_to || '未分配'}</span>
                          <span>更新: {formatDate(alert.updated_at)}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
