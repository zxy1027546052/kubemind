# KubeMind 后续开发计划 (Phase 6 + DeepSeek 集成)

## Context

Phase 3-5 已完成 (语义搜索、智能诊断、告警中心、工作流)。用户已在 `backend/app/config/.env` 中配置了 DeepSeek 大模型和 Kubernetes 集群连接信息。当前有 5 个前端页面仍为占位符 (Dashboard 35%、Models 12%、Clusters 18%、Settings 20%、Topology 8%)。

按照 `develop-plan.md` 路线图，接下来需要:
1. 集成 DeepSeek 大模型 (替换 OpenAI 默认配置 + 实现真实测试连接 + Models 页面)
2. Phase 6: Kubernetes 接入 (集群/节点/Pod 状态)
3. Dashboard 页面从占位符改为真实集群概览

## Part A: DeepSeek 大模型集成 + Models 页面

### 需要修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/core/config.py` | 修改 | 添加 DEEPSEEK_* 和 KUBECONFIG_PATH 配置项 |
| `backend/app/seeds/model_config.py` | 修改 | 将默认 LLM 配置改为 DeepSeek (从 .env 读取)，设为 active=True |
| `backend/app/services/model_config.py` | 修改 | `test_model_connection` 实现真实的 API 连通性测试 |
| `backend/app/services/embedding.py` | 修改 | 泛化为 OpenAI-compatible provider，支持 DeepSeek endpoint |
| `backend/app/services/llm.py` | **新建** | LLM 调用抽象 — 从 diagnosis.py 提取，支持 DeepSeek chat API |
| `backend/app/services/diagnosis.py` | 修改 | 使用新的 `llm.py` 服务替代内联 urllib 调用 |
| `frontend/src/services/api.ts` | 修改 | 添加 ModelConfig CRUD + testConnection API 函数和类型 |
| `frontend/src/pages/Models.tsx` | 重写 | 占位符 → 模型配置表格 + 新建/编辑表单 + 测试连接按钮 |

### 设计要点

- **DeepSeek API 兼容性**: DeepSeek API 与 OpenAI 格式完全兼容 (`/v1/chat/completions`, `/v1/embeddings`)，只需替换 endpoint 和 api_key
- **`llm.py` 服务**: 提供 `chat_completion(messages, model_config) -> str` 和 `get_active_llm_config(db) -> ModelConfig`
- **test_connection**: 发送一条极简 chat completion 请求 (max_tokens=1)，根据 HTTP 状态码判定成功/失败
- **Models 页面**: 配置表格 (name/provider/model_type/is_active)、激活切换、新建/编辑表单 (含 api_key 脱敏)、测试连接按钮+结果提示

## Part B: Kubernetes 集成 (Phase 6)

### 需要新增的文件

| 文件 | 说明 |
|------|------|
| `backend/app/services/k8s.py` | K8s 客户端管理 — 加载 kubeconfig，创建 CoreV1Api/AppsV1Api，提供集群/节点/Pod 查询 |
| `backend/app/api/v1/endpoints/clusters.py` | `GET /api/clusters` (集群列表), `GET /api/clusters/overview` (Dashboard 概览数据) |

### 需要修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/requirements.txt` | 修改 | 添加 `kubernetes` Python 客户端 |
| `backend/app/core/config.py` | 修改 | 添加 `KUBECONFIG_PATH` 配置项 |
| `backend/app/api/v1/router.py` | 修改 | 注册 clusters router |
| `backend/app/core/exceptions.py` | 修改 | 添加 `ClusterConnectionException` |
| `frontend/src/services/api.ts` | 修改 | 添加 ClusterOverview、ClusterInfo 类型和 API 函数 |
| `frontend/src/pages/Clusters.tsx` | 重写 | 占位符 → 集群列表 + 节点状态 + Pod 分布 |
| `frontend/src/pages/Dashboard.tsx` | 重写 | 占位符 → 运维总览 (集群健康、资源使用率、告警概览) |

### 设计要点

- **K8s 客户端初始化**: lifespan startup 时加载 kubeconfig，创建单例 K8sClient
- **安全只读**: 仅使用 ReadOnly 操作 (list/get)，不创建/修改 K8s 资源
- **容错设计**: K8s API 不可达时不阻塞启动，返回健康状态为 `unknown`，前端显示 "集群未连接"
- **集群概览 API**: `GET /api/clusters/overview` 返回:
  ```json
  { "clusters": [{"name": "...", "version": "...", "status": "healthy"}],
    "nodes": {"total": N, "ready": N, "not_ready": N},
    "pods": {"total": N, "running": N, "pending": N, "failed": N},
    "resource_usage": {"cpu_percent": 45, "memory_percent": 62, "disk_percent": 38},
    "alert_summary": {"critical": N, "high": N, "active_total": N} }
  ```

## Part C: 前端页面升级总览

| 页面 | 当前状态 | 目标状态 |
|------|----------|----------|
| Models | 占位符 12% | 模型配置表格 + CRUD + 测试连接 |
| Dashboard | 占位符 35% | 集群健康卡片 + 资源使用率 + 告警概览 |
| Clusters | 占位符 18% | 集群列表 + 节点/Pod 状态表格 |
| Settings | 占位符 20% | 先保留占位符 (P2 优先级) |
| Topology | 占位符 8% | 先保留占位符 (P3 优先级) |

## 新增 API 端点

| 前缀 | 端点 | 说明 |
|------|------|------|
| `/api/models` | (已有) POST `/{id}/test` | test_connection 改为真实检测 |
| `/api/clusters` | GET `/overview` | Dashboard 概览数据 |
| `/api/clusters` | GET | 集群列表 + 状态 |
| `/api/clusters` | GET `/{name}/nodes` | 节点列表 |
| `/api/clusters` | GET `/{name}/pods` | Pod 列表 (支持 namespace 过滤) |

## 验证方式

1. **Models 页面**: 启动前端 → 打开 AI 模型页面 → 应显示 DeepSeek 配置 (从种子数据) → 点击测试连接 → 应返回真实结果
2. **DeepSeek 诊断**: `POST /api/diagnosis` 提交故障描述 → 应通过 DeepSeek API 生成真实诊断报告 (而非规则降级)
3. **Cluster 概览**: `curl http://127.0.0.1:10000/api/clusters/overview` → 返回集群状态数据
4. **Dashboard 页面**: 前端运维总览页面显示真实集群指标卡片
5. **Clusters 页面**: 集群列表显示节点和 Pod 状态
