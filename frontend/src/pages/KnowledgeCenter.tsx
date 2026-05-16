import { useState, useEffect, useCallback } from 'react';
import { api, type Document, type DocumentCreate, type SearchResult } from '../services/api';
import PageErrorBoundary from '../components/PageErrorBoundary';

const TABS = [
  { key: 'case', label: '案例库' },
  { key: 'runbook', label: '运维手册' },
  { key: 'doc', label: '文档管理' },
];

const TYPE_OPTIONS = [
  { value: '', label: '类型筛选' },
  { value: 'Runbook', label: 'Runbook' },
  { value: '案例', label: '案例' },
  { value: '文档', label: '文档' },
];

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

function getTagClass(type: string): string {
  if (type === 'Runbook') return 'tag-runbook';
  if (type === '案例') return 'tag-case';
  return 'tag-doc';
}

export default function KnowledgeCenter() {
  return (
    <PageErrorBoundary title="知识中心加载失败">
      <KnowledgeCenterInner />
    </PageErrorBoundary>
  );
}

function KnowledgeCenterInner() {
  const [activeTab, setActiveTab] = useState('doc');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [viewDoc, setViewDoc] = useState<Document | SearchResult | null>(null);
  const [showViewModal, setShowViewModal] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Upload form state
  const [form, setForm] = useState<DocumentCreate>({
    title: '',
    type: '文档',
    category: '',
    content: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setIsSearching(false);
    try {
      if (searchQuery.trim()) {
        // Semantic search across all sources
        const data = await api.search({ q: searchQuery.trim(), top_k: 20 });
        setSearchResults(data.results);
        setTotal(data.total);
        setIsSearching(true);
      } else {
        const params: { query?: string; category?: string } = {};
        if (typeFilter) params.category = typeFilter;
        const data = await api.listDocuments(params);
        setDocuments(data.items);
        setTotal(data.total);
      }
    } catch (err) {
      showToast('无法连接到后端服务', 'error');
      setDocuments([]);
      setSearchResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, typeFilter]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  function showToast(message: string, type: 'success' | 'error') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  async function handleDelete(id: number) {
    try {
      await api.deleteDocument(id);
      showToast('文档已删除', 'success');
      fetchDocuments();
    } catch {
      showToast('删除失败', 'error');
    }
  }

  async function handleCreate() {
    if (!form.title.trim() || !form.category.trim()) {
      showToast('请填写标题和分类', 'error');
      return;
    }

    setSubmitting(true);
    try {
      await api.createDocument(form);
      showToast('文档创建成功', 'success');
      setShowModal(false);
      setForm({ title: '', type: '文档', category: '', content: '' });
      fetchDocuments();
    } catch {
      showToast('创建失败', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="scan-lines">
      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`} onClick={() => setToast(null)}>
          {toast.type === 'success' ? '✓' : '✗'} {toast.message}
        </div>
      )}

      {/* Page Header */}
      <header className="page-header stagger-1">
        <div className="page-eyebrow">knowledge_center</div>
        <h1>知识中心</h1>
        <p className="subtitle">案例库 · 运维手册 · 文档管理 · 语义搜索</p>
      </header>

      {/* Main Card */}
      <div className="card stagger-2">
        {/* Tabs */}
        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={`tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Toolbar */}
        <div className="toolbar stagger-3">
          <button className="primary" onClick={() => setShowModal(true)}>
            + 上传文档
          </button>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            {TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <div className="spacer" />
          <input
            className="search-input"
            placeholder="> 语义搜索知识库..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchDocuments()}
          />
          <button onClick={fetchDocuments}>搜索</button>
        </div>

        {/* Table */}
        <table className="data-table">
          <thead>
            <tr>
              <th>标题</th>
              {isSearching ? <th>来源</th> : <th>类型</th>}
              {isSearching ? <th>相关度</th> : <th>分类</th>}
              {!isSearching && <th>大小</th>}
              <th>创建时间</th>
              <th style={{ width: 140 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={isSearching ? 5 : 7} style={{ textAlign: 'center', padding: '40px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    搜索中<span style={{ animation: 'cursor-blink 1s step-end infinite' }}>_</span>
                  </span>
                </td>
              </tr>
            ) : isSearching ? (
              searchResults.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="empty-state">
                      <div className="empty-icon">[?]</div>
                      <h3>未找到匹配结果</h3>
                      <p>尝试使用其他关键词搜索</p>
                    </div>
                  </td>
                </tr>
              ) : (
                searchResults.map((r, i) => (
                  <tr key={`${r.source_type}-${r.id}`} className={`stagger-${Math.min(i + 3, 6)}`}>
                    <td className="col-title">{r.title}</td>
                    <td>
                      <span className={`tag ${getTagClass(r.source_type === 'runbooks' ? 'Runbook' : r.source_type === 'cases' ? '案例' : '文档')}`}>
                        {r.source_type === 'runbooks' ? 'Runbook' : r.source_type === 'cases' ? '案例' : '文档'}
                      </span>
                    </td>
                    <td className="col-mono">{Math.round(r.score * 100)}%</td>
                    <td className="col-mono">-</td>
                    <td>
                      <div className="table-actions">
                        <button className="small" onClick={() => { setViewDoc(r); setShowViewModal(true); }}>查看</button>
                      </div>
                    </td>
                  </tr>
                ))
              )
            ) : documents.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-state">
                    <div className="empty-icon">[ ]</div>
                    <h3>暂无文档</h3>
                    <p>上传你的第一篇运维文档或 Runbook</p>
                  </div>
                </td>
              </tr>
            ) : (
              documents.map((doc, i) => (
                <tr key={doc.id} className={`stagger-${Math.min(i + 3, 6)}`}>
                  <td className="col-title">{doc.title}</td>
                  <td>
                    <span className={`tag ${getTagClass(doc.type)}`}>{doc.type}</span>
                  </td>
                  <td className="col-mono">{doc.category}</td>
                  <td className="col-mono">{doc.size || '-'}</td>
                  <td className="col-mono">{formatDate(doc.created_at)}</td>
                  <td>
                    <div className="table-actions">
                      <button className="small" onClick={() => { setViewDoc(doc); setShowViewModal(true); }}>查看</button>
                      <button className="danger" onClick={() => handleDelete(doc.id)}>删除</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Footer */}
        {!loading && (documents.length > 0 || searchResults.length > 0) && (
          <div
            style={{
              padding: '12px 22px',
              borderTop: '1px solid var(--border-subtle)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.6875rem',
              color: 'var(--text-muted)',
            }}
          >
            {isSearching ? `搜索 "${searchQuery}" — ${total} 条结果` : `共 ${total} 条记录`}
          </div>
        )}
      </div>

      {/* View Modal */}
      {showViewModal && viewDoc && (
        <div className="modal-overlay" onClick={() => { setShowViewModal(false); setViewDoc(null); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <h2>文档详情</h2>
              <button className="modal-close" onClick={() => { setShowViewModal(false); setViewDoc(null); }}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>标题</label>
                <div className="view-field">{viewDoc.title}</div>
              </div>
              {'type' in viewDoc && viewDoc.type && (
                <div className="form-group">
                  <label>类型</label>
                  <div className="view-field">
                    <span className={`tag ${getTagClass(viewDoc.type)}`}>{viewDoc.type}</span>
                  </div>
                </div>
              )}
              {'source_type' in viewDoc && viewDoc.source_type && (
                <div className="form-group">
                  <label>来源</label>
                  <div className="view-field">
                    <span className={`tag ${getTagClass(viewDoc.source_type === 'runbooks' ? 'Runbook' : viewDoc.source_type === 'cases' ? '案例' : '文档')}`}>
                      {viewDoc.source_type === 'runbooks' ? 'Runbook' : viewDoc.source_type === 'cases' ? '案例' : '文档'}
                    </span>
                  </div>
                </div>
              )}
              {'score' in viewDoc && (
                <div className="form-group">
                  <label>相关度</label>
                  <div className="view-field">{Math.round(viewDoc.score * 100)}%</div>
                </div>
              )}
              {'category' in viewDoc && viewDoc.category && (
                <div className="form-group">
                  <label>分类</label>
                  <div className="view-field">{viewDoc.category}</div>
                </div>
              )}
              {'size' in viewDoc && viewDoc.size && (
                <div className="form-group">
                  <label>大小</label>
                  <div className="view-field">{viewDoc.size}</div>
                </div>
              )}
              {'created_at' in viewDoc && (
                <div className="form-group">
                  <label>创建时间</label>
                  <div className="view-field">{formatDate(viewDoc.created_at)}</div>
                </div>
              )}
              {'updated_at' in viewDoc && viewDoc.updated_at && (
                <div className="form-group">
                  <label>更新时间</label>
                  <div className="view-field">{formatDate(viewDoc.updated_at)}</div>
                </div>
              )}
              {'content' in viewDoc && viewDoc.content && (
                <div className="form-group">
                  <label>内容</label>
                  <pre className="view-content">{viewDoc.content}</pre>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button onClick={() => { setShowViewModal(false); setViewDoc(null); }}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>上传文档</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="form-group">
                <label>标题 *</label>
                <input
                  placeholder="文档标题..."
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>类型</label>
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                >
                  <option value="文档">文档</option>
                  <option value="Runbook">Runbook</option>
                  <option value="案例">案例</option>
                </select>
              </div>

              <div className="form-group">
                <label>分类 *</label>
                <input
                  placeholder="例如: network_issue, slow_sql..."
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>内容</label>
                <textarea
                  placeholder="文档正文内容..."
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button onClick={() => setShowModal(false)}>取消</button>
              <button className="primary" onClick={handleCreate} disabled={submitting}>
                {submitting ? '提交中...' : '确认上传'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
