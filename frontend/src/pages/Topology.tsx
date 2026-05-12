export default function Topology() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">business_topology</div>
        <h1>业务拓扑</h1>
        <p className="subtitle">服务依赖 · 流量路径 ·  blast radius 分析</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'[●─●─●]'}</div>
        <h2>拓扑图渲染中</h2>
        <p>基于 K8s 服务网格数据的实时拓扑可视化，支持依赖分析与影响面评估。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '8%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
