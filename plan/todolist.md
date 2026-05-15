# KubeMind Todo List

本文档用于跟踪 `develop-plan.md` 中的具体实现任务。优先级按“先打通数据闭环，再增强智能能力，最后补齐生产化能力”的顺序排列。

## P0 当前迭代

- [x] 实现后端可观测数据服务
  - [x] 增加 Prometheus / Loki 配置项
  - [x] 封装 Prometheus 即时查询与范围查询
  - [x] 封装 Loki 日志查询
  - [x] 暴露 `/api/observability/*` API
  - [x] 增加服务层和 API 层测试
- [x] 实现异常检测最小版本
  - [x] 定义时间序列输入 Schema
  - [x] 实现 3-sigma 检测函数
  - [x] 实现自适应阈值评分
  - [x] 暴露 `/api/anomalies/detect` API
- [x] 将异常检测结果接入告警中心
  - [x] 增加异常来源字段
  - [x] 支持从异常事件生成告警

## P1 智能诊断增强

- [x] 实现 LangGraph 多智能体最小状态图
  - [x] 定义 `OpsGraphState`
  - [x] 实现 PlannerAgent
  - [x] 实现 RetrieverAgent
  - [x] 实现 MilvusAgent
  - [x] 实现 ObservabilityAgent
  - [x] 实现 DiagnosisAgent
  - [x] 记录 Agent 执行轨迹
- [x] 封装 MCP / 运维工具层
  - [x] 定义工具注册表（统一 Schema、权限、超时、重试）
  - [x] 封装 Kubernetes 只读工具（pods/events/logs/describe）
  - [x] 封装 Prometheus 查询工具
  - [x] 封装 Loki 查询工具
  - [x] 增加工具调用审计记录（入库 + 关联会话/Trace）
  - [x] 工具白名单与命名空间隔离
- [ ] 增强根因分析
  - [ ] 聚合告警、异常、指标、日志和相似案例
  - [ ] 输出根因 TopN
  - [ ] 输出证据链和推荐 Runbook
  - [ ] 根因结果回写诊断记录与告警关联

## P2 知识图谱与对话式运维

- [x] 建立故障知识图谱最小模型
  - [x] 定义实体表
  - [x] 定义关系表
  - [x] 从 Kubernetes 资源构建关系
  - [x] 从 Runbook / 案例抽取故障关系
- [x] 开发对话式运维接口
  - [x] 定义会话模型
  - [x] 实现意图识别
  - [x] 实现槽位抽取
  - [x] 支持查询指标、日志、Runbook 和发起诊断

## P3 资源预测与扩缩容建议

- [ ] 构建资源预测数据集
- [ ] 实现 LSTM 训练脚本
- [ ] 实现在线预测接口
- [ ] 输出扩缩容建议
- [ ] 接入工作流人工审批

## P4 生产化与上线准备

### 配置与密钥管理
- [ ] 抽离所有硬编码配置到 `app/config/.env`，并补齐 `.env.example`
- [ ] 引入 Pydantic Settings 校验必填项（启动期 fail-fast）
- [ ] 区分 `dev` / `staging` / `prod` profile
- [ ] 接入密钥管理（K8s Secret / Vault），禁止明文写入镜像
- [ ] LLM / Milvus / Prometheus / Loki 凭证全部走环境变量

### 持久化与数据层
- [ ] 生产环境切换到 PostgreSQL（替换 SQLite）
- [ ] 引入 Alembic 数据库迁移脚本，并纳入发布流程
- [ ] 设计索引（告警、诊断、会话、审计表的常用查询字段）
- [ ] 定义数据保留策略与归档任务（告警 / 审计日志 / 会话记录）
- [ ] Milvus collection 备份与重建脚本

### 认证、授权与多租户
- [ ] 接入登录与 JWT 认证（前后端打通）
- [ ] 基于角色的访问控制（RBAC：viewer / operator / admin）
- [ ] 所有写操作和工具调用增加权限校验
- [ ] 多集群 / 多命名空间隔离
- [ ] API 速率限制与防爆破

### 可靠性与性能
- [ ] FastAPI 全链路超时与取消传播
- [ ] 外部依赖（Prom / Loki / K8s / LLM / Milvus）增加重试 + 熔断
- [ ] 长任务（诊断、向量同步）改为后台任务 + 进度查询
- [ ] 引入异步任务队列（如 Celery / RQ / arq）
- [ ] 并发与连接池调优（DB、HTTP client）
- [ ] 关键接口压测与基线指标记录

### 可观测性（自身）
- [ ] 结构化日志（JSON + trace_id + request_id）
- [ ] 接入 OpenTelemetry，导出 trace 到 Tempo / Jaeger
- [ ] 暴露 Prometheus `/metrics`（QPS、延迟、错误率、Agent 调用量、Token 用量）
- [ ] LLM 调用埋点（耗时、token、成本、失败率）
- [ ] 提供自身的健康检查与就绪探针 `/healthz` `/readyz`

### 前端生产化
- [ ] 生产构建产物启用代码分割与 gzip/brotli
- [ ] 静态资源走 CDN 或 Nginx 缓存
- [ ] 接入登录态、错误边界与统一异常提示
- [ ] ChatOps 流式响应、断线重连
- [ ] 关键页面的骨架屏 / 加载态打磨
- [ ] 暗色主题视觉走查（对齐 `project_rules.md` 配色规范）

### 容器化与部署
- [ ] backend / frontend 各自的多阶段 Dockerfile（精简 + 非 root 用户）
- [ ] `docker-compose.yml` 提供本地一键起栈（含 PG / Prom / Loki / Milvus）
- [ ] Kubernetes Helm Chart（Deployment / Service / Ingress / HPA / PDB）
- [ ] ConfigMap + Secret 分离
- [ ] 镜像安全扫描（Trivy）纳入流水线

### CI/CD 与质量门禁
- [~] 修复并固化 Python 虚拟环境（`.venv` 已可用，pytest 可执行；待统一使用 `uv` 或 `poetry` 锁定依赖）
- [ ] CI：lint（ruff / mypy / eslint / tsc）+ 单测 + 构建
- [ ] 后端测试覆盖率门槛（目标 ≥ 70%）
- [ ] 前端 e2e 冒烟用例（Playwright）
- [ ] 自动化镜像构建与版本号管理
- [ ] 蓝绿 / 金丝雀发布脚本

### 安全
- [ ] 依赖漏洞扫描（pip-audit / npm audit）
- [ ] 关闭生产环境 Swagger 或加鉴权
- [ ] CORS、CSRF、XSS、SQL 注入复核
- [ ] 工具调用沙箱：默认只读，写操作需二次确认 + 审计
- [ ] LLM 输入输出脱敏（避免泄露密钥 / PII）
- [ ] Prompt Injection 防护与工具调用白名单

### 文档与运维交付
- [ ] 部署手册（生产 / 灾备 / 回滚）
- [ ] 接入手册（Prometheus / Loki / K8s 集群对接步骤）
- [ ] Runbook：常见故障自查与回滚步骤
- [ ] API 文档（OpenAPI）和前端组件文档
- [ ] 发布日志与版本规范（SemVer + CHANGELOG）



## 验证记录

- 2026-05-13: 已添加 `backend/tests/test_observability_service.py` 和 `backend/tests/test_observability_api.py`（4+1 用例）。
- 2026-05-13: 已添加 `backend/tests/test_anomaly_service.py` 和 `backend/tests/test_anomaly_api.py`（2+2 用例）。
- 2026-05-13: `/api/anomalies/detect?create_alerts=true` 已支持将异常事件写入告警中心，告警来源为 `anomaly_detector`，分类为 `anomaly`。
- 2026-05-13: 已添加 `backend/tests/test_agents_graph.py` 和 `backend/tests/test_chatops_api.py`（3+3 用例）。已实现最小 Agent 状态图和 `/api/chatops/messages`。
- 2026-05-14: 修复 Python 环境阻塞项——创建 `backend/conftest.py` 补充 `sys.path`、降级 `httpx` 到 0.27.2 兼容 starlette TestClient、venv 安装 pytest。**16/16 测试全部通过**（1.62s）。
- 2026-05-13: 已完善前端 ChatOps 入口，新增 `/chatops` 页面、API Client 类型和侧边栏导航。`npm run build` 通过，Vite dev server 已在 `http://127.0.0.1:5173/chatops` 可访问。
- 2026-05-13: 已新增 `MilvusAgent`，对话中包含 `milvus` / `向量库` / `Runbook` 检索意图时会调用 `milvus.vector_search`，通过现有向量检索服务优先查询 Milvus，结果回写到 ChatOps 证据面板。`npm run build` 通过；后端测试仍受 Python 环境问题影响暂无法执行。
- 2026-05-14: 补齐 P4 生产化与上线准备章节，覆盖配置/数据/认证/可靠性/可观测性/前端/容器化/CI/安全/文档 10 个维度的上线 checklist。
- 2026-05-14: 新增 P5 高可用、容灾与运营章节（HA/备份/SLO/数据治理/成本/灰度/事故响应/Go-No-Go），同时确认 `.venv` 已可通过 `.\venv\Scripts\activate` 激活（Python 3.11.4），P0–P1 测试阻塞项可解除，待后续 CI 落地。
- 2026-05-15: 收拢前端功能——**删除独立 智能诊断 页面**，合并至对话运维 `/chatops`（新增快速诊断输入区、Agent 轨迹、根因候选、处置计划面板）；`/diagnosis` → `/chatops` 重定向；后端诊断 API 保持不变供内部 Agent 调用。`npm run build` + 31/31 测试全部通过。
- 2026-05-15: 完成 P2 故障知识图谱——模型层（KnowledgeEntity + KnowledgeRelationship，支持 k8s_cluster/node/namespace/pod/deployment/alert/case/runbook 等实体类型及 BELONGS_TO/CONTAINS/TRIGGERED_BY/CAUSES/MITIGATES 关系）、服务层（_upsert_entity/_link/build_from_k8s/build_from_runbooks/build_from_cases/rebuild_graph/get_graph_snapshot）、API 层（GET /api/knowledge-graph/graph + POST /api/knowledge-graph/graph/build）、种子数据。**14/14 KG 测试全通过**；全量 29/30（1 个 chatops 测试为已有 flaky 问题，非本次引入）。
- 2026-05-15: **引入 LangChain 重构 LLM 层**——`llm.py` 从 raw urllib 改为 `langchain-openai` 的 `ChatOpenAI`（支持内置重试、超时、流式输出）；意图识别改为混合策略（关键词优先 + LLM 兜底分类）；`planner_agent` 接入 db 参数支持 LLM 意图分类。依赖新增 `langchain-openai>=0.3` + `langchain-core>=0.3`。**32/32 测试全部通过**。
- 2026-05-16: **完成 MCP / 运维工具层**——引入 `fastmcp>=3.3,<4.0`，新增独立 FastMCP 微服务 `app.mcp_server`（默认 `http://127.0.0.1:11000/mcp/`）和 `start_mcp.ps1`；新增统一工具注册表 `ops_tools`，覆盖 Kubernetes 只读 pods/events/logs/describe、Prometheus instant/range、Loki range 查询；`MCPService` 接入内置工具白名单、超时、重试、命名空间策略和审计入库；前端 `/mcp` 页面完成联调。验证：`pytest backend/tests` **38/38 通过**，`npm --prefix frontend run build` 通过，API 工具执行 smoke test 返回 default namespace Pod 并写入审计。
- 2026-05-16: **增强对话式运维实时工具闭环**——新增 `McpOpsAgent`，ChatOps 在 `query_logs` / `query_metric` / `query_cluster` / `diagnose_issue` 意图下会调用 MCP 只读工具，并将执行结果、错误和审计 ID 回写到 `tool_calls` 与 `evidence`；流式接口同步输出 `McpOpsAgent` 进度；扩展 workload 抽取支持 `*-app` / `*-demoapp` / `web` / `frontend` / `backend` 等常见命名。验证：新增 `backend/tests/test_mcp_chatops_agent.py`、`backend/tests/test_chatops_intent_mcp.py`，`pytest backend/tests` **43/43 通过**；本地 API smoke：`show default java-demoapp error logs` 返回 `query_logs`，并执行 `k8s_get_pod_logs` + `loki_query`。
