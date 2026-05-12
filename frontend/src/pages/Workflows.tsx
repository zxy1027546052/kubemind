export default function Workflows() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">workflow_engine</div>
        <h1>工作流</h1>
        <p className="subtitle">可编排的自动化运维流程引擎</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'[○→○→○]'}</div>
        <h2>工作流引擎待启动</h2>
        <p>可视化 DAG 编排、条件分支、人工审批节点 — 一切运维操作皆可流程化。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '10%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
