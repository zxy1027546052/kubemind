/* KubeMind API Client — NOC Terminal Edition */

const API_BASE = '/api';

export interface Document {
  id: number;
  title: string;
  type: string;
  category: string;
  size: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreate {
  title: string;
  type: string;
  category: string;
  size?: string;
  content?: string;
}

export interface DocumentListResponse {
  total: number;
  items: Document[];
}

export interface HealthResponse {
  status: string;
  service: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(errorBody || `Request failed: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  listDocuments: (params?: { query?: string; category?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.query) searchParams.set('query', params.query);
    if (params?.category) searchParams.set('category', params.category);
    const qs = searchParams.toString();
    return request<DocumentListResponse>(`/documents${qs ? `?${qs}` : ''}`);
  },

  createDocument: (data: DocumentCreate) =>
    request<Document>('/documents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: 'DELETE' }),

  search: (params: { q: string; type?: string; top_k?: number }) => {
    const sp = new URLSearchParams();
    sp.set('q', params.q);
    if (params.type) sp.set('type', params.type);
    if (params.top_k) sp.set('top_k', String(params.top_k));
    return request<SearchResponse>(`/search?${sp.toString()}`);
  },

  // Alerts
  listAlerts: (params?: { query?: string; severity?: string; status?: string; category?: string; offset?: number; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.query) sp.set('query', params.query);
    if (params?.severity) sp.set('severity', params.severity);
    if (params?.status) sp.set('status', params.status);
    if (params?.category) sp.set('category', params.category);
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<AlertListResponse>(`/alerts${qs ? `?${qs}` : ''}`);
  },

  createAlert: (data: AlertCreate) =>
    request<AlertResponse>('/alerts', { method: 'POST', body: JSON.stringify(data) }),

  getAlert: (id: number) => request<AlertResponse>(`/alerts/${id}`),

  updateAlert: (id: number, data: AlertUpdate) =>
    request<AlertResponse>(`/alerts/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteAlert: (id: number) =>
    request<void>(`/alerts/${id}`, { method: 'DELETE' }),

  // Workflows
  listWorkflows: (params?: { query?: string; category?: string; status?: string; offset?: number; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.query) sp.set('query', params.query);
    if (params?.category) sp.set('category', params.category);
    if (params?.status) sp.set('status', params.status);
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<WorkflowListResponse>(`/workflows${qs ? `?${qs}` : ''}`);
  },

  getWorkflow: (id: number) => request<WorkflowResponse>(`/workflows/${id}`),

  deleteWorkflow: (id: number) =>
    request<void>(`/workflows/${id}`, { method: 'DELETE' }),

  // Model Config
  listModels: (params?: { offset?: number; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<ModelConfigListResponse>(`/models${qs ? `?${qs}` : ''}`);
  },

  createModel: (data: ModelConfigCreate) =>
    request<ModelConfigResponse>('/models', { method: 'POST', body: JSON.stringify(data) }),

  getModel: (id: number) => request<ModelConfigResponse>(`/models/${id}`),

  updateModel: (id: number, data: ModelConfigUpdate) =>
    request<ModelConfigResponse>(`/models/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteModel: (id: number) =>
    request<void>(`/models/${id}`, { method: 'DELETE' }),

  testModelConnection: (id: number) =>
    request<TestConnectionResponse>(`/models/${id}/test`, { method: 'POST' }),

  // Clusters
  getClusterOverview: () => request<ClusterOverview>('/clusters/overview'),

  getClusters: () => request<ClusterOverview['clusters']>('/clusters'),

  getClusterNodes: (name: string) => request<NodeInfo[]>('/clusters/' + name + '/nodes'),

  getClusterPods: (name: string) => request<PodInfo[]>('/clusters/' + name + '/pods'),

  // Observability
  getObservabilityHealth: () =>
    request<ObservabilityHealth>('/observability/health'),

  queryPrometheus: (q: string) => {
    const sp = new URLSearchParams();
    sp.set('q', q);
    return request<PrometheusQueryResponse>(`/observability/prometheus/query?${sp.toString()}`);
  },

  queryLokiRange: (params: { q: string; start: string; end: string; limit?: number }) => {
    const sp = new URLSearchParams();
    sp.set('q', params.q);
    sp.set('start', params.start);
    sp.set('end', params.end);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    return request<LokiQueryResponse>(`/observability/loki/query-range?${sp.toString()}`);
  },

  // Anomalies
  detectAnomalies: (data: AnomalyDetectRequest, options?: { create_alerts?: boolean }) => {
    const sp = new URLSearchParams();
    if (options?.create_alerts) sp.set('create_alerts', 'true');
    const qs = sp.toString();
    return request<AnomalyDetectResponse>(`/anomalies/detect${qs ? `?${qs}` : ''}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // ChatOps
  sendChatOpsMessage: (data: ChatOpsMessageRequest) =>
    request<ChatOpsMessageResponse>('/chatops/messages', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export interface SearchResult {
  id: number;
  source_type: string;
  title: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

// --- Alerts ---

export interface AlertCreate {
  title: string;
  description?: string;
  severity?: string;
  source?: string;
  status?: string;
  assigned_to?: string;
  category?: string;
}

export interface AlertUpdate {
  title?: string;
  description?: string;
  severity?: string;
  source?: string;
  status?: string;
  assigned_to?: string;
  category?: string;
}

export interface AlertResponse {
  id: number;
  title: string;
  description: string;
  severity: string;
  source: string;
  status: string;
  assigned_to: string;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface AlertListResponse {
  pagination: { total: number; offset: number; limit: number };
  items: AlertResponse[];
}

// --- Workflows ---

export interface WorkflowResponse {
  id: number;
  title: string;
  description: string;
  category: string;
  steps: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListResponse {
  pagination: { total: number; offset: number; limit: number };
  items: WorkflowResponse[];
}

export interface WorkflowStep {
  order: number;
  action: string;
  detail: string;
}

// --- Model Config ---

export interface ModelConfigResponse {
  id: number;
  name: string;
  provider: string;
  model_type: string;
  endpoint: string;
  model_name: string;
  is_active: boolean;
  config_json: string;
  created_at: string;
  updated_at: string;
}

export interface ModelConfigCreate {
  name: string;
  provider: string;
  model_type: string;
  endpoint: string;
  api_key: string;
  model_name: string;
  is_active?: boolean;
  config_json?: string;
}

export interface ModelConfigUpdate {
  name?: string;
  provider?: string;
  model_type?: string;
  endpoint?: string;
  api_key?: string;
  model_name?: string;
  is_active?: boolean;
  config_json?: string;
}

export interface ModelConfigListResponse {
  pagination: { total: number; offset: number; limit: number };
  items: ModelConfigResponse[];
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
}

// --- Cluster / Dashboard ---

export interface ClusterOverview {
  clusters: { name: string; version: string; status: string }[];
  nodes: { total: number; ready: number; not_ready: number };
  pods: { total: number; running: number; pending: number; failed: number };
  resource_usage: { cpu_percent: number; memory_percent: number; disk_percent: number };
  alert_summary: { critical: number; high: number; active_total: number };
}

export interface NodeInfo {
  name: string;
  status: string;
  version: string;
  cpu: string;
  memory: string;
}

export interface PodInfo {
  name: string;
  namespace: string;
  status: string;
  node: string;
}

// --- Observability ---

export interface DataSourceHealth {
  enabled: boolean;
  status: string;
  message: string;
}

export interface ObservabilityHealth {
  prometheus: DataSourceHealth;
  loki: DataSourceHealth;
}

export interface PrometheusPoint {
  metric: Record<string, string>;
  timestamp: string;
  value: number;
}

export interface PrometheusQueryResponse {
  query: string;
  result_type: string;
  points: PrometheusPoint[];
}

export interface LokiLogEntry {
  labels: Record<string, string>;
  timestamp: string;
  line: string;
}

export interface LokiQueryResponse {
  query: string;
  entries: LokiLogEntry[];
}

// --- Anomalies ---

export interface MetricPoint {
  timestamp: string;
  value: number;
}

export interface AnomalyDetectRequest {
  metric_name: string;
  resource_type: string;
  resource_name: string;
  namespace?: string;
  window?: string;
  points: MetricPoint[];
}

export interface AnomalyEvent {
  metric_name: string;
  resource_type: string;
  resource_name: string;
  namespace: string;
  window: string;
  value: number;
  baseline: number;
  upper_bound: number;
  lower_bound: number;
  score: number;
  severity: string;
  evidence: string[];
  detected_at: string;
}

export interface AnomalyDetectResponse {
  total: number;
  items: AnomalyEvent[];
  alert_ids: number[];
}

// --- ChatOps ---

export interface ChatOpsMessageRequest {
  session_id?: string;
  message: string;
}

export interface AgentTraceItem {
  agent: string;
  message: string;
}

export interface ChatOpsEvidence {
  source: string;
  title: string;
  summary: string;
  score?: number;
  source_type?: string;
  source_id?: number;
}

export interface ChatOpsToolCall {
  tool: string;
  status: string;
  query?: string;
  namespace?: string;
  workload?: string;
}

export interface ChatOpsRootCause {
  title: string;
  confidence: number;
  evidence_count: number;
}

export interface ChatOpsRemediationStep {
  step: string;
  description: string;
  requires_human_approval: boolean;
}

export interface ChatOpsMessageResponse {
  session_id: string;
  intent: string;
  entities: Record<string, string>;
  reply: string;
  trace: AgentTraceItem[];
  evidence: ChatOpsEvidence[];
  tool_calls: ChatOpsToolCall[];
  root_causes: ChatOpsRootCause[];
  remediation_plan: ChatOpsRemediationStep[];
  requires_human_approval: boolean;
}
