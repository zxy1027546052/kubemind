# Frontend Architecture Optimization Design

**Date:** 2026-05-17
**Status:** Approved

## Overview

Optimize frontend in three areas: state management, error boundaries, and API protocol validation.

---

## 1. State Management — Zustand分层Store

### Current Problems
- ChatOps.tsx holds 6+ `useState`: messages, input, loading, error, expanded, useStream
- useChatOpsStream.ts has local `useState` + `useRef` for SSE stream state
- No global state sharing — sibling components can't access ChatOps state

### Architecture

```
frontend/src/stores/
├── chatOpsStore.ts    # Messages, session, expanded state
├── runtimeStore.ts    # SSE timeline, events, streaming tokens
└── uiStore.ts         # Sidebar, notifications, theme
```

**chatOpsStore** (per-session, per-tab):
- `sessionId`, `messages: ChatMessage[]`, `input`, `useStream: boolean`
- `loading`, `error`, `expanded: Set<number>`
- Actions: `addMessage`, `setLoading`, `setError`, `toggleExpand`, `reset`

**runtimeStore** (per-session):
- `status: 'idle'|'running'|'completed'|'failed'`
- `timeline: TimelineEntry[]`, `events: RuntimeEvent[]`, `streamedTokens: string`
- Actions: `reset`, `processEvent`, `setStatus`

**uiStore** (global):
- `sidebarCollapsed`, `notifications: Notification[]`
- Actions: `toggleSidebar`, `addNotification`, `dismissNotification`

### Migration Strategy
1. Create stores
2. Replace ChatOps.tsx useState with store selectors
3. Replace useChatOpsStream logic with `useChatOpsStore` + `useRuntimeStore` hooks
4. Remove useChatOpsStream hook (or keep thin wrapper)

---

## 2. Error Boundary — Global + Page-Level

### Current Problems
- No React error boundary anywhere
- Any uncaught exception crashes the entire app

### Architecture

```
frontend/src/components/
├── ErrorBoundary.tsx       # Global, catches all unhandled errors
└── PageErrorBoundary.tsx   # Per-page, shows retry button

frontend/src/App.tsx        # Wraps <Router> in ErrorBoundary
frontend/src/pages/*.tsx    # Each page wrapped in PageErrorBoundary
```

**ErrorBoundary**:
- `componentDidCatch` + `getDerivedStateFromError`
- Production: shows "Something went wrong" with error ID
- Development: shows full error message + stack
- Logs to console + optionally to an error reporting service

**PageErrorBoundary**:
- Wraps each page's content (not the layout)
- Shows page-specific error with "Retry" button
- Preserves page shell (sidebar stays visible)

---

## 3. API Protocol Validation — Zod

### Current Problems
- Frontend has no schema validation
- API responses are `as any` typed, no runtime check
- SSE events are processed with raw type casts

### Architecture

```
frontend/src/schemas/
├── chatops.ts    # ChatOpsMessageRequest, ChatOpsMessageResponse, SSE events
├── alerts.ts     # Alert interfaces
├── mcp.ts        # MCP server, tool, audit schemas
└── index.ts      # Re-export all schemas + ApiValidationError

frontend/src/services/api.ts
├── request<T>(path, options, schema?)  # Zod parse after fetch
└── ApiValidationError extends Error     # For type-safe error handling
```

**Validation Flow**:
```
fetch(url) → response.json() → ZodSchema.parse() → typed response
                                    ↓ (if invalid)
                              throws ApiValidationError
```

**SSE Event Validation**:
```typescript
// processEvent receives raw data, validates against known event shapes
const event = SSE_EVENT_SCHEMA.parse(data); // throws on invalid
```

### Schema Coverage (Priority Order)
1. ChatOps: request, response, all SSE event types
2. MCP: tool execution request/response
3. Alerts: create/update/response

---

## Implementation Order

1. **Zod schemas** — foundation, no risk, used by everything else
2. **Error boundaries** — global safety net, independent
3. **Zustand stores** — refactor ChatOps first, then generalize
4. **Wire everything** — connect stores to components, remove old hooks

---

## Files to Create/Modify

### New Files
- `frontend/src/stores/chatOpsStore.ts`
- `frontend/src/stores/runtimeStore.ts`
- `frontend/src/stores/uiStore.ts`
- `frontend/src/schemas/chatops.ts`
- `frontend/src/schemas/alerts.ts`
- `frontend/src/schemas/mcp.ts`
- `frontend/src/schemas/index.ts`
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/components/PageErrorBoundary.tsx`

### Modified Files
- `frontend/src/services/api.ts` — integrate Zod validation
- `frontend/src/hooks/useChatOpsStream.ts` — thin wrapper over store
- `frontend/src/pages/ChatOps.tsx` — use Zustand store
- `frontend/src/App.tsx` — add global ErrorBoundary
- `frontend/src/pages/Alerts.tsx` — add PageErrorBoundary + Zod types
- `frontend/src/pages/MCP.tsx` — add PageErrorBoundary + Zod types
- `frontend/package.json` — add `zustand`, `zod`
