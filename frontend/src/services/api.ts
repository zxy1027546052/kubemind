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
};
