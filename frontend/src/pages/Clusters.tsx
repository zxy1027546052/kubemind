export default function Clusters() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">cluster_management</div>
        <h1>集群管理</h1>
        <p className="subtitle">多集群纳管 · 节点监控 · 资源调度</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'[☷]'}</div>
        <h2>集群纳管模块待接入</h2>
        <p>Kubernetes API 集成将在核心模块完成后启动，支持多集群统一管理。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '18%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
