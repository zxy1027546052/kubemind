export default function Dashboard() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">operations_overview</div>
        <h1>运维总览</h1>
        <p className="subtitle">集群健康 · 资源水位 · 关键指标一览</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">[▓▓░░░░░░]</div>
        <h2>仪表盘构建中</h2>
        <p>实时集群指标、资源拓扑和告警概览即将上线</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '35%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
