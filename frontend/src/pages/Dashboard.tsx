import { useState, useEffect } from 'react';
import { api, type ClusterOverview } from '../services/api';

export default function Dashboard() {
  const [data, setData] = useState<ClusterOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetch() {
      try {
        const d = await api.getClusterOverview();
        setData(d);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  if (loading) {
    return (
      <div>
        <header className="page-header stagger-1">
          <div className="page-eyebrow">operations_overview</div>
          <h1>运维总览</h1>
          <p className="subtitle">集群健康 · 资源水位 · 关键指标一览</p>
        </header>
        <div style={{ textAlign: 'center', padding: '60px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
          加载中<span style={{ animation: 'cursor-blink 1s step-end infinite' }}>_</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <header className="page-header stagger-1">
          <div className="page-eyebrow">operations_overview</div>
          <h1>运维总览</h1>
          <p className="subtitle">集群健康 · 资源水位 · 关键指标一览</p>
        </header>
        <div className="placeholder-page stagger-2">
          <div className="ph-icon">[!]</div>
          <h2>集群未连接</h2>
          <p>{error || '无法获取集群数据，请检查 K8s 配置和网络连通性'}</p>
        </div>
      </div>
    );
  }

  const cluster = data.clusters[0];
  const clusterConnected = cluster?.status === 'healthy';

  const cards = [
    { label: '集群状态', value: clusterConnected ? 'HEALTHY' : 'OFFLINE', color: clusterConnected ? 'var(--accent-green)' : 'var(--accent-red)', subtitle: cluster?.version || '-' },
    { label: '节点', value: `${data.nodes.ready}/${data.nodes.total}`, color: data.nodes.not_ready > 0 ? 'var(--accent-amber)' : 'var(--accent-green)', subtitle: `${data.nodes.not_ready} NotReady` },
    { label: 'Pods', value: `${data.pods.running}/${data.pods.total}`, color: data.pods.failed > 0 ? 'var(--accent-red)' : 'var(--accent-green)', subtitle: `${data.pods.pending} Pending, ${data.pods.failed} Failed` },
    { label: '活跃告警', value: String(data.alert_summary.active_total), color: data.alert_summary.critical > 0 ? 'var(--accent-red)' : 'var(--text-primary)', subtitle: `${data.alert_summary.critical} Critical, ${data.alert_summary.high} High` },
  ];

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">operations_overview</div>
        <h1>运维总览</h1>
        <p className="subtitle">集群健康 · 资源水位 · 关键指标一览</p>
      </header>

      {/* Status Cards */}
      <div className="stagger-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {cards.map((card) => (
          <div key={card.label} className="card" style={{ padding: '20px' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
              {card.label}
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: card.color, marginBottom: '4px' }}>
              {card.value}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>
              {card.subtitle}
            </div>
          </div>
        ))}
      </div>

      {/* Detail Cards */}
      <div className="stagger-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '16px' }}>
        {/* Resource Usage */}
        <div className="card" style={{ padding: '20px' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>资源使用率</h3>
          {[
            { label: 'CPU', pct: data.resource_usage.cpu_percent, color: 'var(--accent-cyan)' },
            { label: 'Memory', pct: data.resource_usage.memory_percent, color: 'var(--accent-purple)' },
            { label: 'Disk', pct: data.resource_usage.disk_percent, color: 'var(--accent-amber)' },
          ].map((r) => (
            <div key={r.label} style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>{r.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{r.pct}%</span>
              </div>
              <div className="progress-bar" style={{ width: '100%' }}>
                <div className="progress-fill" style={{ width: `${Math.min(r.pct, 100)}%`, marginLeft: 0, background: r.color }} />
              </div>
            </div>
          ))}
          {data.resource_usage.cpu_percent === 0 && data.resource_usage.memory_percent === 0 && (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)', textAlign: 'center', padding: '12px' }}>
              K8s metrics-server 未安装或无数据
            </div>
          )}
        </div>

        {/* Pod Distribution */}
        <div className="card" style={{ padding: '20px' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>Pod 分布</h3>
          {[
            { label: 'Running', count: data.pods.running, color: 'var(--accent-green)' },
            { label: 'Pending', count: data.pods.pending, color: 'var(--accent-amber)' },
            { label: 'Failed', count: data.pods.failed, color: 'var(--accent-red)' },
          ].map((p) => (
            <div key={p.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: p.color }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-primary)' }}>{p.label}</span>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: p.color, fontWeight: 700 }}>{p.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
