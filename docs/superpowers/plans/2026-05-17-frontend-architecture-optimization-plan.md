# Frontend Architecture Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Zustand state management, React Error Boundaries, and Zod runtime validation to the frontend.

**Architecture:** Zustand stores replace scattered useState/useCallback in ChatOps; ErrorBoundary components wrap App and pages; Zod schemas validate API responses at runtime via a typed request wrapper.

**Tech Stack:** zustand, zod, React 18

---

## File Map

### New Files
```
frontend/src/stores/chatOpsStore.ts       # ChatOps session state
frontend/src/stores/runtimeStore.ts       # SSE stream/runtime state
frontend/src/stores/uiStore.ts           # Global UI state
frontend/src/schemas/chatops.ts           # Zod schemas for ChatOps API + SSE
frontend/src/schemas/alerts.ts            # Zod schemas for Alerts
frontend/src/schemas/mcp.ts               # Zod schemas for MCP
frontend/src/schemas/index.ts             # Re-exports + ApiValidationError
frontend/src/components/ErrorBoundary.tsx  # Global error boundary
frontend/src/components/PageErrorBoundary.tsx # Per-page error boundary with retry
```

### Modified Files
```
frontend/src/services/api.ts              # Integrate Zod validation in request()
frontend/src/hooks/useChatOpsStream.ts    # Thin wrapper: delegates to runtimeStore
frontend/src/pages/ChatOps.tsx             # Replace 6+ useState with chatOpsStore + runtimeStore
frontend/src/App.tsx                      # Wrap Router in global ErrorBoundary
frontend/src/pages/Alerts.tsx             # Add PageErrorBoundary + Zod types
frontend/src/pages/MCP.tsx                # Add PageErrorBoundary + Zod types
frontend/package.json                     # Add zustand, zod
```

---

## Dependencies

**Task 0: Install dependencies**

- [ ] **Step 1: Add zustand and zod to package.json**

```bash
cd d:\python_project\kubemind\frontend
npm install zustand zod
npm install --save-dev @types/react@18
```

---

## Part 1: Zod Schemas (Foundation)

**Task 1: Create Zod schema files**

- [ ] **Step 1: Create `frontend/src/schemas/chatops.ts`**

```typescript
import { z } from 'zod';

export const ChatOpsMessageRequestSchema = z.object({
  session_id: z.string().optional(),
  message: z.string().min(1),
});
export type ChatOpsMessageRequest = z.infer<typeof ChatOpsMessageRequestSchema>;

export const RootCauseSchema = z.object({
  title: z.string(),
  confidence: z.number(),
  evidence_count: z.number(),
});
export type RootCause = z.infer<typeof RootCauseSchema>;

export const RemediationStepSchema = z.object({
  step: z.string(),
  description: z.string(),
  requires_human_approval: z.boolean().optional(),
});
export type RemediationStep = z.infer<typeof RemediationStepSchema>;

export const ToolCallSchema = z.object({
  tool: z.string(),
  status: z.string().optional(),
  namespace: z.string().optional(),
  workload: z.string().optional(),
  query: z.string().optional(),
  audit_id: z.number().nullable().optional(),
  duration_ms: z.number().optional(),
});
export type ToolCall = z.infer<typeof ToolCallSchema>;

export const EvidenceSchema = z.object({
  source: z.string(),
  title: z.string(),
  summary: z.string().optional(),
  score: z.number().optional(),
  source_type: z.string().optional(),
  source_id: z.number().optional(),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const TraceEntrySchema = z.object({
  agent: z.string(),
  message: z.string(),
});
export type TraceEntry = z.infer<typeof TraceEntrySchema>;

export const ChatOpsMessageResponseSchema = z.object({
  session_id: z.string(),
  intent: z.string(),
  entities: z.record(z.string()),
  reply: z.string().optional(),
  trace: z.array(TraceEntrySchema),
  evidence: z.array(EvidenceSchema),
  tool_calls: z.array(ToolCallSchema),
  root_causes: z.array(RootCauseSchema),
  remediation_plan: z.array(RemediationStepSchema),
  requires_human_approval: z.boolean(),
  llm_reply: z.string().optional(),
});
export type ChatOpsMessageResponse = z.infer<typeof ChatOpsMessageResponseSchema>;

// SSE Event schemas
export const AgentEventSchema = z.object({
  type: z.enum(['agent.started', 'agent.completed', 'agent.failed']),
  agent: z.string(),
  execution_id: z.string().optional(),
  duration_ms: z.number().optional(),
  status: z.string().optional(),
  error: z.string().optional(),
  timestamp: z.string(),
});
export type AgentEvent = z.infer<typeof AgentEventSchema>;

export const ToolEventSchema = z.object({
  type: z.enum(['tool.started', 'tool.completed', 'tool.failed', 'tool.stdout']),
  tool: z.string(),
  execution_id: z.string().optional(),
  agent_execution_id: z.string().optional(),
  args: z.record(z.unknown()).optional(),
  duration_ms: z.number().optional(),
  risk_level: z.string().optional(),
  chunk: z.string().optional(),
  error: z.string().optional(),
  timestamp: z.string(),
});
export type ToolEvent = z.infer<typeof ToolEventSchema>;

export const EvidenceEventSchema = z.object({
  type: z.literal('evidence.added'),
  source: z.string(),
  title: z.string(),
  summary: z.string(),
  timestamp: z.string(),
});
export type EvidenceEvent = z.infer<typeof EvidenceEventSchema>;

export const DiagnosisEventSchema = z.object({
  type: z.literal('diagnosis.updated'),
  root_causes: z.array(z.object({
    title: z.string(),
    confidence: z.number(),
    evidence_count: z.number(),
  })).optional(),
  remediation_plan: z.array(z.object({
    step: z.string(),
    description: z.string(),
    requires_human_approval: z.boolean(),
  })).optional(),
  timestamp: z.string(),
});
export type DiagnosisEvent = z.infer<typeof DiagnosisEventSchema>;

export const RuntimeEventSchema = z.union([
  AgentEventSchema,
  ToolEventSchema,
  EvidenceEventSchema,
  DiagnosisEventSchema,
]);
export type RuntimeEvent = z.infer<typeof RuntimeEventSchema>;
```

- [ ] **Step 2: Create `frontend/src/schemas/alerts.ts`**

```typescript
import { z } from 'zod';

export const AlertCreateSchema = z.object({
  title: z.string().min(1),
  description: z.string().optional(),
  severity: z.string().optional(),
  source: z.string().optional(),
  status: z.string().optional(),
  assigned_to: z.string().optional(),
  category: z.string().optional(),
});
export type AlertCreate = z.infer<typeof AlertCreateSchema>;

export const AlertUpdateSchema = AlertCreateSchema.partial();
export type AlertUpdate = z.infer<typeof AlertUpdateSchema>;

export const AlertResponseSchema = z.object({
  id: z.number(),
  title: z.string(),
  description: z.string(),
  severity: z.string(),
  source: z.string(),
  status: z.string(),
  assigned_to: z.string(),
  category: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type AlertResponse = z.infer<typeof AlertResponseSchema>;
```

- [ ] **Step 3: Create `frontend/src/schemas/mcp.ts`**

```typescript
import { z } from 'zod';

export const ToolExecuteRequestSchema = z.object({
  tool_name: z.string().min(1),
  params: z.record(z.unknown()).optional(),
  session_id: z.string().optional(),
  trace_id: z.string().optional(),
  namespace: z.string().optional(),
});
export type ToolExecuteRequest = z.infer<typeof ToolExecuteRequestSchema>;

export const ToolExecuteResponseSchema = z.object({
  success: z.boolean(),
  result: z.unknown().optional(),
  error: z.string().optional(),
  duration_ms: z.number(),
  audit_id: z.number().nullable().optional(),
});
export type ToolExecuteResponse = z.infer<typeof ToolExecuteResponseSchema>;
```

- [ ] **Step 4: Create `frontend/src/schemas/index.ts`**

```typescript
export class ApiValidationError extends Error {
  constructor(
    public readonly path: string,
    public readonly issues: z.ZodIssue[],
  ) {
    super(`API validation failed at ${path}: ${issues.map(i => i.message).join(', ')}`);
    this.name = 'ApiValidationError';
  }
}

export function parseSchema<T>(schema: z.ZodType<T>, data: unknown, path: string): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new ApiValidationError(path, result.error.issues);
  }
  return result.data;
}

export * from './chatops';
export * from './alerts';
export * from './mcp';
```

---

## Part 2: Error Boundaries

**Task 2: Create ErrorBoundary components**

- [ ] **Step 1: Create `frontend/src/components/ErrorBoundary.tsx`**

```typescript
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorId: string | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorId: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: `err-${Date.now().toString(36)}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-root)',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-mono)',
        }}>
          <div style={{ textAlign: 'center', maxWidth: 480, padding: 24 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>💥</div>
            <h2 style={{ marginBottom: 8 }}>Something went wrong</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
              Error ID: <code>{this.state.errorId}</code>
            </p>
            {import.meta.env.DEV && this.state.error && (
              <pre style={{
                textAlign: 'left',
                background: 'var(--bg-elevated)',
                padding: 16,
                borderRadius: 4,
                overflow: 'auto',
                fontSize: 12,
                marginBottom: 16,
              }}>
                {this.state.error.message}
                {'\n\n'}
                {this.state.error.stack}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '10px 24px',
                background: 'var(--accent-cyan)',
                color: '#000',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontFamily: 'var(--font-display)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Create `frontend/src/components/PageErrorBoundary.tsx`**

```typescript
import { Component, ReactNode } from 'react';
import ErrorBoundary from './ErrorBoundary';

interface Props {
  children: ReactNode;
  title?: string;
}

export default function PageErrorBoundary({ children, title }: Props) {
  return (
    <ErrorBoundary
      fallback={
        <div style={{
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 400,
          gap: 16,
        }}>
          <span style={{ fontSize: 32 }}>⚠️</span>
          <h3>{title || 'Page Error'}</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            This section encountered an error. Try refreshing.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 20px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              borderRadius: 4,
              cursor: 'pointer',
              fontFamily: 'var(--font-display)',
              fontSize: '0.8125rem',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Reload
          </button>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
```

---

## Part 3: Zustand Stores

**Task 3: Create runtimeStore**

- [ ] **Step 1: Create `frontend/src/stores/runtimeStore.ts`**

```typescript
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
  addTimelineEntry: (entry: TimelineEntry) => void;
  appendStreamedToken: (token: string) => void;
  addEvent: (event: StreamEvent) => void;
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

  addTimelineEntry: (entry) =>
    set((s) => ({ timeline: [...s.timeline, entry] })),

  appendStreamedToken: (token) =>
    set((s) => ({ streamedTokens: s.streamedTokens + token })),

  addEvent: (event) =>
    set((s) => ({ events: [...s.events, event as StreamEvent] })),

  processServerEvent: (eventType, data) => {
    const timestamp = (data.timestamp as string) || new Date().toISOString();
    const time = formatTime(timestamp);

    set((s) => {
      const newTimeline = [...s.timeline];
      const newEvents = [...s.events];

      switch (eventType) {
        case 'agent.started':
          newTimeline.push({ time, type: 'agent', label: `${data.agent} started`, status: 'running' });
          newEvents.push({ type: 'agent.started', agent: data.agent as string, timestamp });
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
          });
          break;
        case 'agent.failed':
          newTimeline.push({ time, type: 'agent', label: `${data.agent} failed`, status: 'failed' });
          newEvents.push({ type: 'agent.failed', agent: data.agent as string, error: data.error as string, timestamp });
          break;
        case 'tool.started':
          newTimeline.push({
            time, type: 'tool', label: `${data.tool}`,
            detail: JSON.stringify(data.args || {}), status: 'running',
          });
          newEvents.push({ type: 'tool.started', tool: data.tool as string, args: data.args as Record<string, unknown>, timestamp });
          break;
        case 'tool.completed':
          newTimeline.push({
            time, type: 'tool', label: `${data.tool} done`,
            status: 'success', duration_ms: data.duration_ms as number | undefined,
          });
          newEvents.push({ type: 'tool.completed', tool: data.tool as string, duration_ms: data.duration_ms as number | undefined, timestamp });
          break;
        case 'tool.failed':
          newTimeline.push({ time, type: 'tool', label: `${data.tool} failed`, status: 'failed' });
          newEvents.push({ type: 'tool.failed', tool: data.tool as string, error: data.error as string, timestamp });
          break;
        case 'evidence.added':
          newTimeline.push({ time, type: 'evidence', label: `[${data.source}] ${data.title}`, detail: data.summary as string });
          newEvents.push({ type: 'evidence.added', source: data.source as string, title: data.title as string, summary: data.summary as string, timestamp });
          break;
        case 'diagnosis.updated':
          newEvents.push({ type: 'diagnosis.updated', root_causes: data.root_causes as DiagnosisEvent['root_causes'], remediation_plan: data.remediation_plan as DiagnosisEvent['remediation_plan'], timestamp });
          break;
        case 'token':
          if (typeof data.content === 'string') {
            set((st) => ({ streamedTokens: st.streamedTokens + data.content }));
          }
          break;
      }

      return { timeline: newTimeline, events: newEvents };
    });
  },
}));
```

**Task 4: Create chatOpsStore**

- [ ] **Step 1: Create `frontend/src/stores/chatOpsStore.ts`**

```typescript
import { create } from 'zustand';
import type { ChatOpsMessageResponse } from '../schemas/chatops';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  result?: ChatOpsMessageResponse;
}

interface ChatOpsState {
  sessionId: string;
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  error: string;
  expanded: Set<number>;
  useStream: boolean;
}

interface ChatOpsActions {
  setInput: (input: string) => void;
  addMessage: (message: ChatMessage) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string) => void;
  toggleExpand: (index: number) => void;
  setUseStream: (useStream: boolean) => void;
  reset: () => void;
}

function makeSessionId() {
  return `chat-${Date.now().toString(36)}`;
}

const initialState: ChatOpsState = {
  sessionId: makeSessionId(),
  messages: [],
  input: '',
  loading: false,
  error: '',
  expanded: new Set(),
  useStream: true,
};

export const useChatOpsStore = create<ChatOpsState & ChatOpsActions>((set) => ({
  ...initialState,

  setInput: (input) => set({ input }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  toggleExpand: (index) =>
    set((s) => {
      const next = new Set(s.expanded);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return { expanded: next };
    }),

  setUseStream: (useStream) => set({ useStream }),

  reset: () => set({ ...initialState, sessionId: makeSessionId(), expanded: new Set() }),
}));
```

**Task 5: Create uiStore**

- [ ] **Step 1: Create `frontend/src/stores/uiStore.ts`**

```typescript
import { create } from 'zustand';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timeout?: number;
}

interface UiState {
  sidebarCollapsed: boolean;
  notifications: Notification[];
}

interface UiActions {
  toggleSidebar: () => void;
  addNotification: (n: Omit<Notification, 'id'>) => void;
  dismissNotification: (id: string) => void;
}

export const useUiStore = create<UiState & UiActions>((set) => ({
  sidebarCollapsed: false,
  notifications: [],

  toggleSidebar: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  addNotification: (n) => {
    const id = `notif-${Date.now().toString(36)}`;
    set((s) => ({ notifications: [...s.notifications, { ...n, id }] }));
    if (n.timeout !== 0) {
      setTimeout(() => {
        set((s) => ({ notifications: s.notifications.filter((x) => x.id !== id) }));
      }, n.timeout ?? 4000);
    }
  },

  dismissNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),
}));
```

---

## Part 4: API Layer with Zod

**Task 6: Update api.ts with Zod validation**

- [ ] **Step 1: Modify `frontend/src/services/api.ts`**

Add Zod validation to the `request` function. Find the existing `request` function (around line 24) and replace it:

```typescript
import { z } from 'zod';
import { parseSchema, ApiValidationError } from '../schemas';

async function request<T>(
  path: string,
  options?: RequestInit,
  schema?: z.ZodType<T>,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(errorBody || `Request failed: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;

  const data = await res.json();

  if (schema) {
    try {
      return parseSchema(schema, data, path);
    } catch (e) {
      if (e instanceof ApiValidationError) {
        console.warn('[API Validation]', e.path, e.issues);
      }
      throw e;
    }
  }

  return data as T;
}
```

Then update the ChatOps call to use the schema:

```typescript
// In the api object, find sendChatOpsMessage and update:
sendChatOpsMessage: (data: ChatOpsMessageRequest) =>
  request<ChatOpsMessageResponse>('/chatops/messages', {
    method: 'POST',
    body: JSON.stringify(data),
  }, ChatOpsMessageResponseSchema),
```

Similarly update `executeTool` to use `ToolExecuteResponseSchema`.

---

## Part 5: Wire Components

**Task 7: Update App.tsx with global ErrorBoundary**

- [ ] **Step 1: Modify `frontend/src/App.tsx`**

Add ErrorBoundary wrapping Router. The file currently ends with:

```typescript
// Should wrap the return value:
return (
  <ErrorBoundary>
    <Router />
  </ErrorBoundary>
);
```

**Task 8: Refactor ChatOps.tsx to use Zustand**

- [ ] **Step 1: Modify `frontend/src/pages/ChatOps.tsx`**

Replace the top-level useState block:

```typescript
// OLD (remove):
// const [sessionId] = useState(() => `chat-${Date.now().toString(36)}`);
// const [input, setInput] = useState('');
// const [messages, setMessages] = useState<ChatMessage[]>([]);
// const [loading, setLoading] = useState(false);
// const [error, setError] = useState('');
// const [expanded, setExpanded] = useState<Set<number>>(new Set());
// const [useStream, setUseStream] = useState(true);
// const { runtime, sendMessage, reset } = useChatOpsStream();

// NEW:
const { sessionId, messages, input, loading, error, expanded, useStream, setInput, addMessage, setLoading, setError, toggleExpand, setUseStream, reset: resetChatOps } = useChatOpsStore();
const { status: runtimeStatus, timeline, streamedTokens, events, reset: resetRuntime, setStatus, processServerEvent } = useRuntimeStore();
const abortRef = useRef<AbortController | null>(null);

async function handleSend() {
  const text = input.trim();
  if (!text || loading) return;

  setLoading(true);
  setError('');
  addMessage({ role: 'user', content: text });
  setInput('');
  resetRuntime();

  try {
    if (useStream) {
      // SSE stream logic using processServerEvent + setStatus
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
              const typed = data as ChatOpsMessageResponse;
              const reply = streamedTokens || typed?.reply || '';
              addMessage({ role: 'assistant', content: reply, result: typed });
            }
            eventType = '';
          }
        }
      }
      setStatus('completed');
    } else {
      const result = await api.sendChatOpsMessage({ session_id: sessionId, message: text });
      addMessage({ role: 'assistant', content: result.reply, result });
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : '对话请求失败';
    setError(msg);
    addMessage({ role: 'assistant', content: `ERR: ${msg}` });
  } finally {
    setLoading(false);
  }
}
```

Also update all references: `toggleExpand(index)` stays the same, `expanded.has(index)` stays the same. Replace `runtime.streamedTokens` → `streamedTokens`, `runtime.status` → `runtimeStatus`, `runtime.events` → `events`, `runtime.timeline` → `timeline`, `runtime.reset()` → `resetChatOps()`.

**Task 9: Simplify useChatOpsStream hook**

- [ ] **Step 1: Modify `frontend/src/hooks/useChatOpsStream.ts`**

The hook should become a thin wrapper that exposes `sendMessage` + delegates to runtimeStore. Keep the file but simplify it:

```typescript
import { useCallback, useRef } from 'react';
import { useRuntimeStore } from '../stores/runtimeStore';
import { useChatOpsStore } from '../stores/chatOpsStore';
import { api } from '../services/api';

export function useChatOpsStream() {
  const abortRef = useRef<AbortController | null>(null);
  const { reset: resetRuntime, processServerEvent, setStatus, streamedTokens } = useRuntimeStore();
  const { sessionId, useStream, addMessage, setLoading, setError, setInput } = useChatOpsStore();

  const reset = useCallback(() => {
    resetRuntime();
  }, [resetRuntime]);

  const sendMessage = useCallback(async (sessionId: string, message: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus('running');

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
            processServerEvent(eventType, data);
            if (eventType === 'done') {
              return data;
            }
            eventType = '';
          }
        }
      }
      setStatus('completed');
      return null;
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setStatus('failed');
      }
      return null;
    }
  }, [sessionId, useStream, processServerEvent, setStatus, addMessage, setLoading, setError]);

  return {
    runtime: { status: useRuntimeStore.getState().status, streamedTokens, timeline: useRuntimeStore.getState().timeline, events: useRuntimeStore.getState().events },
    sendMessage,
    abort: () => abortRef.current?.abort(),
    reset,
  };
}
```

Note: Keep this file because ChatOps.tsx currently uses it. After Task 8, ChatOps.tsx won't need it anymore — the store will be the source of truth. You can delete useChatOpsStream.ts after verifying ChatOps works with direct store access.

**Task 10: Add PageErrorBoundary to pages**

- [ ] **Step 1: Wrap each page export in PageErrorBoundary in each page file**

In `Alerts.tsx`, `MCP.tsx`, `Clusters.tsx`, `Dashboard.tsx`, `KnowledgeCenter.tsx`, `Models.tsx`, `Settings.tsx`, `Topology.tsx`, `Workflows.tsx`:

```typescript
// At the bottom or as default, wrap the page:
export default function PageErrorBoundaryWrapper() {
  return (
    <PageErrorBoundary title="Alerts Page Error">
      <AlertsContent />
    </PageErrorBoundary>
  );
}
```

Where `AlertsContent` is the renamed original function (the one currently exported as `default`).

---

## Verification

**Task 11: Verify ChatOps works**

- [ ] **Step 1: Start backend and frontend, test ChatOps flow**

```bash
cd d:\python_project\kubemind\backend
python -m uvicorn app.main:app --reload --port 12000

# In another terminal:
cd d:\python_project\kubemind\frontend
npm run dev
```

- Navigate to http://localhost:5173/chatops
- Send a message: "查一下 prod payment-api 的 CPU 指标"
- Verify: streaming tokens appear, timeline updates, no console errors

**Task 12: Verify Error Boundary works**

- [ ] **Step 1: Test global ErrorBoundary**

Add temporary bad render to a component:
```typescript
// In ChatOps.tsx temporarily:
throw new Error('test error');
```
Verify: page shows error UI with ID, not blank page.
Remove the test code immediately.

- [ ] **Step 2: Remove test code and verify normal operation**

---

## Cleanup

**Task 13: Delete useChatOpsStream after verification**

After confirming ChatOps works with direct store access, delete `frontend/src/hooks/useChatOpsStream.ts` and remove its import from `ChatOps.tsx`.
