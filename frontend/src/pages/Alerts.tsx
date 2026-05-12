export default function Alerts() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">alert_governance</div>
        <h1>告警中心</h1>
        <p className="subtitle">告警聚合 · 降噪 · 升级 · 闭环治理</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'!!!'}</div>
        <h2>告警通道未接入</h2>
        <p>Prometheus AlertManager 集成将在后续阶段完成，届时支持告警聚合与智能降噪。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '5%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
