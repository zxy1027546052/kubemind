import { useState, useEffect } from 'react';
import { api, type ClusterOverview, type NodeInfo, type PodInfo } from '../services/api';

export default function Clusters() {
  const [overview, setOverview] = useState<ClusterOverview | null>(null);
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [pods, setPods] = useState<PodInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'nodes' | 'pods'>('nodes');

  useEffect(() => {
    async function fetchData() {
      try {
        const [ov, nd, pd] = await Promise.all([
          api.getClusterOverview(),
          api.getClusterNodes('default'),
          api.getClusterPods('default'),
        ]);
        setOverview(ov);
        setNodes(nd);
        setPods(pd);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div>
        <header className="page-header stagger-1">
          <div className="page-eyebrow">cluster_management</div>
          <h1>集群管理</h1>
          <p className="subtitle">多集群纳管 · 节点监控 · 资源调度</p>
        </header>
        <div style={{ textAlign: 'center', padding: '60px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
          连接集群中<span style={{ animation: 'cursor-blink 1s step-end infinite' }}>_</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <header className="page-header stagger-1">
          <div className="page-eyebrow">cluster_management</div>
          <h1>集群管理</h1>
          <p className="subtitle">多集群纳管 · 节点监控 · 资源调度</p>
        </header>
        <div className="placeholder-page stagger-2">
          <div className="ph-icon">[x]</div>
          <h2>集群连接失败</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const cluster = overview?.clusters[0];

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">cluster_management</div>
        <h1>集群管理</h1>
        <p className="subtitle">多集群纳管 · 节点监控 · 资源调度</p>
      </header>

      {/* Cluster Info Card */}
      {cluster && (
        <div className="card stagger-2" style={{ padding: '20px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div className={`status-dot ${cluster.status === 'healthy' ? '' : 'offline'}`} style={{ width: '12px', height: '12px' }} />
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', color: 'var(--text-primary)' }}>
                {cluster.name}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Version: {cluster.version} · Status: {cluster.status}
              </div>
            </div>
            <div className="spacer" />
            <div style={{ display: 'flex', gap: '24px', textAlign: 'right' }}>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>NODES</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--accent-cyan)' }}>{overview?.nodes.total || 0}</div>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', color: 'var(--text-muted)' }}>PODS</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--accent-purple)' }}>{overview?.pods.total || 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="card stagger-3">
        <div className="tabs">
          <button className={`tab ${activeTab === 'nodes' ? 'active' : ''}`} onClick={() => setActiveTab('nodes')}>
            节点列表 ({nodes.length})
          </button>
          <button className={`tab ${activeTab === 'pods' ? 'active' : ''}`} onClick={() => setActiveTab('pods')}>
            Pod 列表 ({pods.length})
          </button>
        </div>

        {activeTab === 'nodes' ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>节点名称</th>
                <th>状态</th>
                <th>版本</th>
                <th>CPU</th>
                <th>内存</th>
              </tr>
            </thead>
            <tbody>
              {nodes.length === 0 ? (
                <tr><td colSpan={5}><div className="empty-state"><div className="empty-icon">[N]</div><h3>未发现节点</h3><p>集群可能未连接或没有工作节点</p></div></td></tr>
              ) : nodes.map((n, i) => (
                <tr key={n.name}>
                  <td className="col-title">{n.name}</td>
                  <td><span className={`tag ${n.status === 'Ready' ? 'tag-runbook' : 'tag-case'}`}>{n.status}</span></td>
                  <td className="col-mono">{n.version}</td>
                  <td className="col-mono">{n.cpu}</td>
                  <td className="col-mono">{n.memory}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Pod 名称</th>
                <th>命名空间</th>
                <th>状态</th>
                <th>节点</th>
              </tr>
            </thead>
            <tbody>
              {pods.length === 0 ? (
                <tr><td colSpan={4}><div className="empty-state"><div className="empty-icon">[P]</div><h3>未发现 Pod</h3><p>集群可能没有运行中的工作负载</p></div></td></tr>
              ) : pods.slice(0, 50).map((p, i) => (
                <tr key={`${p.namespace}/${p.name}`}>
                  <td className="col-title">{p.name}</td>
                  <td className="col-mono">{p.namespace}</td>
                  <td><span className={`tag ${p.status === 'Running' ? 'tag-runbook' : p.status === 'Pending' ? 'tag-doc' : 'tag-case'}`}>{p.status}</span></td>
                  <td className="col-mono">{p.node}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
