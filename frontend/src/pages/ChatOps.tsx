import { useCallback, useRef } from 'react';
import { api } from '../services/api';
import { useChatOpsStore } from '../stores/chatOpsStore';
import { useRuntimeStore } from '../stores/runtimeStore';
import type { ChatOpsMessageResponse } from '../schemas/chatops';
import PageErrorBoundary from '../components/PageErrorBoundary';
import DagView from '../components/DagView';

function MarkdownText({ text }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  for (const line of lines) {
    const key = `md-${elements.length}`;
    if (line.startsWith('## ')) {
      elements.push(<h3 key={key} className="markdown-h2">{line.slice(3)}</h3>);
    } else if (line.startsWith('### ')) {
      elements.push(<h4 key={key} className="markdown-h3">{line.slice(4)}</h4>);
    } else if (line.startsWith('- ')) {
      elements.push(<div key={key} className="markdown-list-item">{line}</div>);
    } else if (line.match(/^\d+\. /)) {
      elements.push(<div key={key} className="markdown-ordered-item">{line}</div>);
    } else if (line.includes('**')) {
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const richParts = parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={`${key}-b-${i}`} className="markdown-bold">{part.slice(2, -2)}</strong>;
        }
        return <span key={`${key}-s-${i}`}>{part}</span>;
      });
      elements.push(<p key={key} className="markdown-p">{richParts}</p>);
    } else if (line.includes('`')) {
      const parts = line.split(/(`.*?`)/g);
      const richParts = parts.map((part, i) => {
        if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={`${key}-c-${i}`} className="markdown-code">{part.slice(1, -1)}</code>;
        }
        return <span key={`${key}-s-${i}`}>{part}</span>;
      });
      elements.push(<p key={key} className="markdown-p">{richParts}</p>);
    } else if (line.trim()) {
      elements.push(<p key={key} className="markdown-p">{line}</p>);
    } else {
      elements.push(<br key={key} />);
    }
  }

  return <div className="markdown-content">{elements}</div>;
}

const EXAMPLES = [
  '帮我分析 prod payment-api 最近错误日志',
  '查一下 prod payment-api 的 CPU 指标',
  '找一下磁盘满的处理手册',
  '看 payment-api 最近错误日志',
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
    general_chat: '通用对话',
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

function TimelinePanel({ entries, status }: { entries: { time: string; type: string; label: string; detail?: string; status?: 'running' | 'success' | 'failed'; duration_ms?: number }[]; status: string }) {
  if (entries.length === 0 && status === 'idle') return null;

  return (
    <div className="runtime-timeline">
      <div className="timeline-header">
        <span className="timeline-title">Runtime Timeline</span>
        {status === 'running' && <span className="timeline-status pulse">running</span>}
        {status === 'completed' && <span className="timeline-status done">done</span>}
      </div>
      <div className="timeline-entries">
        {entries.map((entry, i) => (
          <div key={i} className={`timeline-entry ${entry.status || ''} ${entry.type}`}>
            <span className="timeline-time">{entry.time}</span>
            <span className={`timeline-dot ${entry.status || 'info'}`} />
            <span className="timeline-label">{entry.label}</span>
            {entry.duration_ms != null && (
              <span className="timeline-duration">{entry.duration_ms}ms</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ChatOpsInner() {
  const {
    sessionId, messages, input, loading, error, expanded, useStream,
    setInput, addMessage, setLoading, setError, toggleExpand, setUseStream, reset: resetChat,
  } = useChatOpsStore();

  const { status, timeline, reset: resetRuntime, processServerEvent, setStatus, getCurrentTokens } = useRuntimeStore();

  const handleClearHistory = useCallback(() => {
    resetChat();
    resetRuntime();
  }, [resetChat, resetRuntime]);

  const abortRef = useRef<AbortController | null>(null);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    setLoading(true);
    setError('');
    addMessage({ role: 'user', content: text });
    setInput('');
    resetRuntime();

    try {
      if (useStream) {
        abortRef.current?.abort();
        const controller = new AbortController();
        abortRef.current = controller;

        setStatus('running');

        const res = await fetch('/api/chatops/messages/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message: text }),
          signal: controller.signal,
        });

        if (!res.ok) throw new Error(`Stream failed: ${res.status}`);
        if (!res.body) throw new Error('No response body');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult: ChatOpsMessageResponse | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let eventType = '';
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ') && eventType) {
              const data = JSON.parse(line.slice(6));
              processServerEvent(eventType, data);
              if (eventType === 'done') {
                finalResult = data as ChatOpsMessageResponse;
              }
              eventType = '';
            }
          }
        }

        setStatus('completed');
        const reply = getCurrentTokens() || finalResult?.reply || '';
        addMessage({ role: 'assistant', content: reply, result: finalResult || undefined });
      } else {
        const result = await api.sendChatOpsMessage({ session_id: sessionId, message: text });
        addMessage({ role: 'assistant', content: result.reply, result });
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        const msg = err instanceof Error ? err.message : '对话请求失败';
        setError(msg);
        addMessage({ role: 'assistant', content: `ERR: ${msg}` });
        setStatus('failed');
      }
    } finally {
      setLoading(false);
    }
  }, [input, loading, useStream, sessionId, setInput, addMessage, setLoading, setError, resetRuntime, processServerEvent, setStatus, getCurrentTokens]);

  function renderDetail(result: ChatOpsMessageResponse, index: number) {
    const isExpanded = expanded.has(index);
    const hasDetail =
      result.trace.length > 0 ||
      result.tool_calls.length > 0 ||
      result.evidence.length > 0 ||
      result.root_causes.length > 0 ||
      result.remediation_plan.length > 0 ||
      Object.keys(result.entities).length > 0;

    if (!hasDetail) return null;

    return (
      <div className="msg-detail">
        <button type="button" className="msg-detail-toggle" onClick={() => toggleExpand(index)}>
          <span className={`msg-detail-arrow ${isExpanded ? 'open' : ''}`}>&#9654;</span>
          {isExpanded ? '收起分析详情' : '查看分析详情'}
        </button>

        {isExpanded && (
          <div className="msg-detail-body">
            {Object.keys(result.entities).length > 0 && (
              <div className="msg-detail-section">
                <h4>槽位</h4>
                <div className="msg-kv">
                  {Object.entries(result.entities).map(([key, value]) => (
                    <div key={key}>
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.trace.length > 0 && (
              <div className="msg-detail-section">
                <h4>Agent 执行轨迹</h4>
                <div className="agent-timeline">
                  {result.trace.map((item, i) => (
                    <div key={`${item.agent}-${i}`} className="agent-step">
                      <div className="agent-index">{i + 1}</div>
                      <div>
                        <div className="agent-name">{item.agent}</div>
                        <div className="agent-message">{item.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.tool_calls.length > 0 && (
              <div className="msg-detail-section">
                <h4>工具调用计划</h4>
                <div className="tool-list">
                  {result.tool_calls.map((tool, i) => (
                    <div key={`${tool.tool}-${i}`} className="tool-item">
                      <span>{tool.tool}</span>
                      <strong>{tool.status}</strong>
                      <p>{tool.query || [tool.namespace, tool.workload].filter(Boolean).join(' / ') || '-'}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.evidence.length > 0 && (
              <div className="msg-detail-section">
                <h4>证据</h4>
                <div className="evidence-list">
                  {result.evidence.map((item, i) => (
                    <div key={`${item.source}-${i}`} className={`evidence-item ${item.source === 'milvus' ? 'milvus-hit' : ''}`}>
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
                  ))}
                </div>
              </div>
            )}

            {result.root_causes.length > 0 && (
              <div className="msg-detail-section">
                <h4>根因候选</h4>
                <div className="rootcause-list">
                  {result.root_causes.map((item, i) => (
                    <div key={`${item.title}-${i}`} className="rootcause-item">
                      <div>
                        <strong>{item.title}</strong>
                        <span>{item.evidence_count} evidence</span>
                      </div>
                      <em>{confidenceText(item.confidence)}</em>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.remediation_plan.length > 0 && (
              <div className="msg-detail-section">
                <h4>处置计划</h4>
                <div className="remediation-list">
                  {result.remediation_plan.map((item, i) => (
                    <div key={`${item.step}-${i}`} className="remediation-item">
                      <strong>{item.step}</strong>
                      <p>{item.description}</p>
                      {item.requires_human_approval && <span className="tag warn">需人工确认</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="chatops-layout">
      <div className="chatops-main">
        <header className="page-header stagger-1">
          <div className="page-eyebrow">chatops_console</div>
          <h1>对话式运维</h1>
          <p className="subtitle">自然语言意图识别 · Agent 编排 · 工具调用轨迹 · 智能诊断</p>
        </header>

        <section className="card chatops-console stagger-2">
          <div className="card-header">
            <h3>会话终端</h3>
            <div className="card-header-actions">
              <button type="button" className="ghost" onClick={handleClearHistory}>
                清理历史
              </button>
              <label className="stream-toggle">
                <input type="checkbox" checked={useStream} onChange={(e) => setUseStream(e.target.checked)} />
                <span>Stream</span>
              </label>
              <span className="chatops-session">{sessionId}</span>
            </div>
          </div>

          <div className="chatops-messages">
            {messages.length === 0 ? (
              <div className="chatops-empty">
                <div className="chatops-empty-code">READY</div>
                <p>输入自然语言运维指令，系统将识别意图、抽取槽位，并通过 Agent 状态图生成查询和诊断计划。</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`chat-message ${message.role}`}>
                  <div className="chat-role">{message.role === 'user' ? 'operator' : 'kubemind'}</div>
                  <div className="chat-bubble">
                    {message.result && (
                      <div className="msg-chips">
                        <span className="msg-chip intent">{intentLabel(message.result.intent)}</span>
                        <span className="msg-chip">{message.result.trace.length} agents</span>
                        <span className="msg-chip">{message.result.tool_calls.length} tools</span>
                        {message.result.requires_human_approval && (
                          <span className="msg-chip warn">需人工确认</span>
                        )}
                      </div>
                    )}
                    <div className="chat-text">
                      {message.role === 'assistant' ? (
                        <MarkdownText text={message.content} />
                      ) : (
                        <span>{message.content}</span>
                      )}
                    </div>
                    {message.result && renderDetail(message.result, index)}
                  </div>
                </div>
              ))
            )}
            {loading && getCurrentTokens() && (
              <div className="chat-message assistant">
                <div className="chat-role">kubemind</div>
                <div className="chat-bubble">
                  <div className="chat-text streaming">{getCurrentTokens()}<span className="cursor" /></div>
                </div>
              </div>
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
      </div>

      <aside className="chatops-sidebar">
        <DagView events={[]} />
        <TimelinePanel entries={timeline} status={status} />
      </aside>
    </div>
  );
}

export default function ChatOps() {
  return (
    <PageErrorBoundary title="对话式运维加载失败">
      <ChatOpsInner />
    </PageErrorBoundary>
  );
}
