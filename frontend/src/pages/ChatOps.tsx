import { useMemo, useState } from 'react';
import { api, type ChatOpsMessageResponse } from '../services/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  result?: ChatOpsMessageResponse;
}

const EXAMPLES = [
  '查询 milvus 里面磁盘满的处理手册',
  '查一下 prod payment-api 的 CPU 指标',
  '看 payment-api 最近错误日志',
  '帮我分析 prod payment-api 最近错误日志',
  '找一下磁盘满的处理手册',
  '生成排查流程',
];

function intentLabel(intent: string): string {
  const labels: Record<string, string> = {
    query_metric: '指标查询',
    query_logs: '日志查询',
    diagnose_issue: '故障诊断',
    search_runbook: 'Runbook 检索',
    create_workflow: '流程创建',
    query_cluster: '集群查询',
  };
  return labels[intent] || intent;
}

function confidenceText(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function sourceLabel(source: string): string {
  if (source === 'milvus') return 'MILVUS';
  if (source === 'observability') return 'OBS';
  if (source === 'knowledge') return 'KB';
  return source.toUpperCase();
}

export default function ChatOps() {
  const [sessionId] = useState(() => `chat-${Date.now().toString(36)}`);
  const [input, setInput] = useState('查一下 prod payment-api 的 CPU 指标');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeResult, setActiveResult] = useState<ChatOpsMessageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const agentCount = useMemo(() => activeResult?.trace.length ?? 0, [activeResult]);
  const toolCount = useMemo(() => activeResult?.tool_calls.length ?? 0, [activeResult]);

  async function handleSend() {
    const message = input.trim();
    if (!message || loading) return;

    setLoading(true);
    setError('');
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setInput('');

    try {
      const result = await api.sendChatOpsMessage({ session_id: sessionId, message });
      setActiveResult(result);
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply, result }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '对话请求失败';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'assistant', content: `ERR: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <header className="page-header stagger-1">
        <div className="page-eyebrow">chatops_console</div>
        <h1>对话式运维</h1>
        <p className="subtitle">自然语言意图识别 · Agent 编排 · 工具调用轨迹</p>
      </header>

      <div className="chatops-grid stagger-2">
        <section className="card chatops-console">
          <div className="card-header">
            <h3>会话终端</h3>
            <span className="chatops-session">{sessionId}</span>
          </div>

          <div className="chatops-messages">
            {messages.length === 0 ? (
              <div className="chatops-empty">
                <div className="chatops-empty-code">READY</div>
                <p>输入运维问题后，系统会识别意图、抽取槽位，并通过 Agent 状态图生成查询和诊断计划。</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`chat-message ${message.role}`}>
                  <div className="chat-role">{message.role === 'user' ? 'operator' : 'kubemind'}</div>
                  <div className="chat-bubble">{message.content}</div>
                </div>
              ))
            )}
          </div>

          {error && <div className="chatops-error">{error}</div>}

          <div className="chatops-examples">
            {EXAMPLES.map((example) => (
              <button key={example} type="button" onClick={() => setInput(example)}>
                {example}
              </button>
            ))}
          </div>

          <div className="chatops-input-row">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSend();
              }}
              rows={3}
              placeholder="输入运维指令，例如: 查一下 prod payment-api 的 CPU 指标"
            />
            <button className="primary" onClick={handleSend} disabled={loading || !input.trim()}>
              {loading ? '运行中' : '发送'}
            </button>
          </div>
        </section>

        <aside className="chatops-side">
          <div className="card chatops-summary">
            <div className="metric-tile">
              <span>Intent</span>
              <strong>{activeResult ? intentLabel(activeResult.intent) : '-'}</strong>
            </div>
            <div className="metric-tile">
              <span>Agents</span>
              <strong>{agentCount}</strong>
            </div>
            <div className="metric-tile">
              <span>Tools</span>
              <strong>{toolCount}</strong>
            </div>
            <div className="metric-tile">
              <span>Approval</span>
              <strong className={activeResult?.requires_human_approval ? 'warn' : ''}>
                {activeResult?.requires_human_approval ? 'YES' : 'NO'}
              </strong>
            </div>
          </div>

          <div className="card chatops-panel">
            <div className="card-header">
              <h3>槽位</h3>
            </div>
            <div className="chatops-kv">
              {activeResult && Object.keys(activeResult.entities).length > 0 ? (
                Object.entries(activeResult.entities).map(([key, value]) => (
                  <div key={key}>
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </div>
                ))
              ) : (
                <p>等待识别</p>
              )}
            </div>
          </div>
        </aside>
      </div>

      {activeResult && (
        <div className="chatops-detail-grid stagger-3">
          <section className="card chatops-panel">
            <div className="card-header">
              <h3>Agent 执行轨迹</h3>
            </div>
            <div className="agent-timeline">
              {activeResult.trace.map((item, index) => (
                <div key={`${item.agent}-${index}`} className="agent-step">
                  <div className="agent-index">{index + 1}</div>
                  <div>
                    <div className="agent-name">{item.agent}</div>
                    <div className="agent-message">{item.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card chatops-panel">
            <div className="card-header">
              <h3>工具调用计划</h3>
            </div>
            <div className="tool-list">
              {activeResult.tool_calls.length > 0 ? (
                activeResult.tool_calls.map((tool, index) => (
                  <div key={`${tool.tool}-${index}`} className="tool-item">
                    <span>{tool.tool}</span>
                    <strong>{tool.status}</strong>
                    <p>{tool.query || [tool.namespace, tool.workload].filter(Boolean).join(' / ') || '-'}</p>
                  </div>
                ))
              ) : (
                <div className="empty-inline">无工具调用计划</div>
              )}
            </div>
          </section>

          <section className="card chatops-panel">
            <div className="card-header">
              <h3>证据</h3>
            </div>
            <div className="evidence-list">
              {activeResult.evidence.length > 0 ? (
                activeResult.evidence.map((item, index) => (
                  <div key={`${item.source}-${index}`} className={`evidence-item ${item.source === 'milvus' ? 'milvus-hit' : ''}`}>
                    <div className="evidence-meta">
                      <span>{sourceLabel(item.source)}</span>
                      {typeof item.score === 'number' && <em>{confidenceText(item.score)}</em>}
                    </div>
                    <strong>{item.title}</strong>
                    <p>{item.summary}</p>
                    {(item.source_type || item.source_id) && (
                      <div className="evidence-ref">
                        {item.source_type || 'source'}#{item.source_id ?? '-'}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="empty-inline">等待 Agent 收集证据</div>
              )}
            </div>
          </section>

          <section className="card chatops-panel">
            <div className="card-header">
              <h3>根因候选</h3>
            </div>
            <div className="rootcause-list">
              {activeResult.root_causes.map((item, index) => (
                <div key={`${item.title}-${index}`} className="rootcause-item">
                  <div>
                    <strong>{item.title}</strong>
                    <span>{item.evidence_count} evidence</span>
                  </div>
                  <em>{confidenceText(item.confidence)}</em>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
