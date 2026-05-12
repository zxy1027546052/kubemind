export default function Diagnosis() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">intelligent_diagnosis</div>
        <h1>智能诊断</h1>
        <p className="subtitle">AI 驱动的故障根因分析与诊断建议</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'{-_-}'}</div>
        <h2>诊断引擎离线</h2>
        <p>LangChain + LangGraph 诊断链路正在集成中。届时将支持多轮交互式排障。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '15%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
