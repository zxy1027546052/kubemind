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

  // Diagnosis
  createDiagnosis: (data: DiagnosisCreate) =>
    request<DiagnosisResponse>('/diagnosis', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getDiagnosis: (id: number) =>
    request<DiagnosisResponse>(`/diagnosis/${id}`),

  listDiagnoses: (params?: { offset?: number; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return request<DiagnosisResponse[]>(`/diagnosis${qs ? `?${qs}` : ''}`);
  },

  deleteDiagnosis: (id: number) =>
    request<void>(`/diagnosis/${id}`, { method: 'DELETE' }),

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

// --- Diagnosis ---

export interface DiagnosisCreate {
  query_text: string;
}

export interface MatchedItem {
  id: number;
  source_type: string;
  title: string;
  score: number;
}

export interface DiagnosisResult {
  root_causes: string[];
  steps: string[];
  impact: string;
  runbook_refs: { id: number; title: string; score: number }[];
}

export interface DiagnosisResponse {
  id: number;
  query_text: string;
  matched_items: MatchedItem[];
  llm_response: DiagnosisResult;
  status: string;
  created_at: string;
  updated_at: string;
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
