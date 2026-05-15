import { useCallback, useRef, useState } from 'react';

export interface AgentEvent {
  type: 'agent.started' | 'agent.completed' | 'agent.failed';
  agent: string;
  execution_id?: string;
  duration_ms?: number;
  status?: string;
  error?: string;
  timestamp: string;
}

export interface ToolEvent {
  type: 'tool.started' | 'tool.completed' | 'tool.failed' | 'tool.stdout';
  tool: string;
  execution_id?: string;
  agent_execution_id?: string;
  args?: Record<string, unknown>;
  duration_ms?: number;
  risk_level?: string;
  chunk?: string;
  error?: string;
  timestamp: string;
}

export interface EvidenceEvent {
  type: 'evidence.added';
  source: string;
  title: string;
  summary: string;
  timestamp: string;
}

export interface DiagnosisEvent {
  type: 'diagnosis.updated';
  root_causes?: Array<{ title: string; confidence: number; evidence_count: number }>;
  remediation_plan?: Array<{ step: string; description: string; requires_human_approval: boolean }>;
  timestamp: string;
}

export type RuntimeEvent = AgentEvent | ToolEvent | EvidenceEvent | DiagnosisEvent;

export interface TimelineEntry {
  time: string;
  type: string;
  label: string;
  detail?: string;
  status?: 'running' | 'success' | 'failed';
  duration_ms?: number;
}

export interface RuntimeState {
  status: 'idle' | 'running' | 'completed' | 'failed';
  timeline: TimelineEntry[];
  streamedTokens: string;
  events: RuntimeEvent[];
}

const initialState: RuntimeState = {
  status: 'idle',
  timeline: [],
  streamedTokens: '',
  events: [],
};

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

export function useChatOpsStream() {
  const [runtime, setRuntime] = useState<RuntimeState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setRuntime(initialState);
  }, []);

  const sendMessage = useCallback(async (sessionId: string, message: string): Promise<unknown | null> => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRuntime({ ...initialState, status: 'running' });

    let finalResult: unknown = null;

    try {
      const res = await fetch('/api/chatops/messages/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`Stream failed: ${res.status}`);
      if (!res.body) throw new Error('No response body');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

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
            processEvent(eventType, data, setRuntime);
            if (eventType === 'done') {
              finalResult = data;
            }
            eventType = '';
          }
        }
      }

      setRuntime(prev => ({ ...prev, status: 'completed' }));
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setRuntime(prev => ({ ...prev, status: 'failed' }));
      }
    }

    return finalResult;
  }, []);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setRuntime(prev => ({ ...prev, status: 'idle' }));
  }, []);

  return { runtime, sendMessage, abort, reset };
}

function processEvent(
  type: string,
  data: Record<string, unknown>,
  setState: React.Dispatch<React.SetStateAction<RuntimeState>>,
) {
  const timestamp = (data.timestamp as string) || new Date().toISOString();
  const time = formatTime(timestamp);

  switch (type) {
    case 'agent.started':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'agent',
          label: `${data.agent} started`,
          status: 'running',
        }],
        events: [...prev.events, { type: 'agent.started', ...data, timestamp } as AgentEvent],
      }));
      break;

    case 'agent.completed':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'agent',
          label: `${data.agent} completed`,
          status: 'success',
          duration_ms: data.duration_ms as number | undefined,
        }],
        events: [...prev.events, { type: 'agent.completed', ...data, timestamp } as AgentEvent],
      }));
      break;

    case 'agent.failed':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'agent',
          label: `${data.agent} failed: ${data.error || ''}`,
          status: 'failed',
        }],
        events: [...prev.events, { type: 'agent.failed', ...data, timestamp } as AgentEvent],
      }));
      break;

    case 'tool.started':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'tool',
          label: `${data.tool}`,
          detail: JSON.stringify(data.args || {}),
          status: 'running',
        }],
        events: [...prev.events, { type: 'tool.started', ...data, timestamp } as ToolEvent],
      }));
      break;

    case 'tool.completed':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'tool',
          label: `${data.tool} done`,
          status: 'success',
          duration_ms: data.duration_ms as number | undefined,
        }],
        events: [...prev.events, { type: 'tool.completed', ...data, timestamp } as ToolEvent],
      }));
      break;

    case 'tool.failed':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'tool',
          label: `${data.tool} failed`,
          status: 'failed',
        }],
        events: [...prev.events, { type: 'tool.failed', ...data, timestamp } as ToolEvent],
      }));
      break;

    case 'evidence.added':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'evidence',
          label: `[${data.source}] ${data.title}`,
          detail: data.summary as string,
        }],
        events: [...prev.events, { type: 'evidence.added', ...data, timestamp } as EvidenceEvent],
      }));
      break;

    case 'diagnosis.updated':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'diagnosis',
          label: 'Diagnosis updated',
        }],
        events: [...prev.events, { type: 'diagnosis.updated', ...data, timestamp } as DiagnosisEvent],
      }));
      break;

    case 'token':
      setState(prev => ({
        ...prev,
        streamedTokens: prev.streamedTokens + ((data.content as string) || ''),
      }));
      break;

    case 'approval.required':
      setState(prev => ({
        ...prev,
        timeline: [...prev.timeline, {
          time,
          type: 'approval',
          label: `Approval required: ${data.tool}`,
          detail: `risk: ${data.risk_level}`,
        }],
      }));
      break;
  }
}
