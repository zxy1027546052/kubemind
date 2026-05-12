export default function Models() {
  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">ai_model_config</div>
        <h1>AI 模型</h1>
        <p className="subtitle">模型配置 · 知识库连接 · RAG 参数调优</p>
      </header>

      <div className="placeholder-page stagger-2">
        <div className="ph-icon">{'[ML]'}</div>
        <h2>模型配置面板建设中</h2>
        <p>支持多模型切换、Embedding 配置、向量数据库连接及 RAG 检索策略调整。</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: '12%', marginLeft: 0, animation: 'none' }} />
        </div>
      </div>
    </div>
  );
}
