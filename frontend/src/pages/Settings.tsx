export default function Settings() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">system_settings</div>
        <h1>系统配置</h1>
        <p className="subtitle">连接配置 · 用户管理 · 全局参数</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'[*]'}</div>
        <h2>配置中心</h2>
        <p>K8s 集群连接、数据源配置、通知渠道及全局参数管理。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '20%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
