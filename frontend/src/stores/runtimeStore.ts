import { create } from 'zustand';
import type { AgentEvent, EvidenceEvent, DiagnosisEvent, ToolEvent } from '../schemas/chatops';

export type RuntimeStatus = 'idle' | 'running' | 'completed' | 'failed';

export interface TimelineEntry {
  time: string;
  type: string;
  label: string;
  detail?: string;
  status?: 'running' | 'success' | 'failed';
  duration_ms?: number;
}

export type StreamEvent = AgentEvent | ToolEvent | EvidenceEvent | DiagnosisEvent;

interface RuntimeState {
  status: RuntimeStatus;
  timeline: TimelineEntry[];
  streamedTokens: string;
  events: StreamEvent[];
}

interface RuntimeActions {
  reset: () => void;
  setStatus: (status: RuntimeStatus) => void;
  processServerEvent: (eventType: string, data: Record<string, unknown>) => void;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

const initialState: RuntimeState = {
  status: 'idle',
  timeline: [],
  streamedTokens: '',
  events: [],
};

export const useRuntimeStore = create<RuntimeState & RuntimeActions>((set) => ({
  ...initialState,

  reset: () => set(initialState),

  setStatus: (status) => set({ status }),

  processServerEvent: (eventType, data) => {
    const timestamp = (data.timestamp as string) || new Date().toISOString();
    const time = formatTime(timestamp);

    set((s) => {
      const newTimeline = [...s.timeline];
      const newEvents = [...s.events];

      switch (eventType) {
        case 'agent.started':
          newTimeline.push({ time, type: 'agent', label: `${data.agent} started`, status: 'running' });
          newEvents.push({ type: 'agent.started', agent: data.agent as string, timestamp } as AgentEvent);
          break;

        case 'agent.completed':
          newTimeline.push({
            time,
            type: 'agent',
            label: `${data.agent} completed`,
            status: 'success',
            duration_ms: data.duration_ms as number | undefined,
          });
          newEvents.push({
            type: 'agent.completed',
            agent: data.agent as string,
            duration_ms: data.duration_ms as number | undefined,
            timestamp,
          } as AgentEvent);
          break;

        case 'agent.failed':
          newTimeline.push({ time, type: 'agent', label: `${data.agent} failed`, status: 'failed' });
          newEvents.push({
            type: 'agent.failed',
            agent: data.agent as string,
            error: data.error as string,
            timestamp,
          } as AgentEvent);
          break;

        case 'tool.started':
          newTimeline.push({
            time, type: 'tool', label: `${data.tool}`,
            detail: JSON.stringify(data.args || {}), status: 'running',
          });
          newEvents.push({
            type: 'tool.started',
            tool: data.tool as string,
            args: data.args as Record<string, unknown>,
            timestamp,
          } as ToolEvent);
          break;

        case 'tool.completed':
          newTimeline.push({
            time, type: 'tool', label: `${data.tool} done`,
            status: 'success', duration_ms: data.duration_ms as number | undefined,
          });
          newEvents.push({
            type: 'tool.completed',
            tool: data.tool as string,
            duration_ms: data.duration_ms as number | undefined,
            timestamp,
          } as ToolEvent);
          break;

        case 'tool.failed':
          newTimeline.push({ time, type: 'tool', label: `${data.tool} failed`, status: 'failed' });
          newEvents.push({
            type: 'tool.failed',
            tool: data.tool as string,
            error: data.error as string,
            timestamp,
          } as ToolEvent);
          break;

        case 'evidence.added':
          newTimeline.push({ time, type: 'evidence', label: `[${data.source}] ${data.title}`, detail: data.summary as string });
          newEvents.push({
            type: 'evidence.added',
            source: data.source as string,
            title: data.title as string,
            summary: data.summary as string,
            timestamp,
          } as EvidenceEvent);
          break;

        case 'diagnosis.updated':
          newEvents.push({
            type: 'diagnosis.updated',
            root_causes: data.root_causes as DiagnosisEvent['root_causes'],
            remediation_plan: data.remediation_plan as DiagnosisEvent['remediation_plan'],
            timestamp,
          } as DiagnosisEvent);
          break;

        case 'token':
          if (typeof data.content === 'string') {
            return { streamedTokens: s.streamedTokens + data.content };
          }
          break;

        case 'done': {
          const reply = (data.llm_reply as string) || s.streamedTokens;
          if (reply !== s.streamedTokens) {
            return { streamedTokens: reply };
          }
          break;
        }
      }

      return { timeline: newTimeline, events: newEvents };
    });
  },
}));
