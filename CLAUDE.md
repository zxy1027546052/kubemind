# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KubeMind is an AI-powered Kubernetes operations platform (运维平台). It combines a React frontend dashboard with a FastAPI backend that orchestrates LLM-driven agents for cluster diagnostics, alerting, and automated remediation.

## Development Commands

### Backend (FastAPI)

```bash
cd backend
# Run the API server (port 12000)
uvicorn app.main:app --host 127.0.0.1 --port 12000 --reload

# Run the MCP server standalone (port 11000)
python -m app.mcp_server

# Run tests
pytest
pytest tests/test_chatops_api.py -v          # single test file
pytest tests/test_chatops_api.py::test_name  # single test

# Install dependencies
pip install -r requirements.txt
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev    # dev server on port 5173, proxies /api → backend:12000
npm run build  # production build
```

### Full Stack

Start backend on port 12000 and frontend on port 5173. The Vite dev server proxies all `/api` requests to the backend.

## Architecture

### Agent Pipeline (LangGraph)

The core intelligence lives in `backend/app/agents/`. ChatOps messages flow through a LangGraph StateGraph:

```
planner → [general_chat? → diagnosis] OR [retriever → milvus → observability → [mcp_ops?] → diagnosis]
```

- **OpsGraphState** (`agents/state.py`): TypedDict carrying session context through the pipeline
- **planner_agent**: Classifies intent (diagnose_issue, query_metric, general_chat, etc.) and extracts entities
- **retriever_agent**: Prepares knowledge-base evidence for non-trivial intents
- **milvus_agent**: Vector similarity search via Milvus
- **observability_agent**: Queries Prometheus/Loki for metrics and logs
- **mcp_ops_agent**: Executes Kubernetes operations tools for actionable intents
- **diagnosis_agent**: Synthesizes findings into root causes and remediation plans via LLM

Falls back to sequential execution if LangGraph fails (`agents/graph.py`).

### Backend Layers

- **API routes**: `app/api/v1/endpoints/` — REST endpoints grouped by domain
- **Services**: `app/services/` — business logic (LLM calls, K8s client, vector search, ops tools)
- **Repositories**: `app/repositories/` — SQLAlchemy data access
- **Models**: `app/models/` — SQLAlchemy ORM models
- **Schemas**: `app/schemas/` — Pydantic request/response models
- **Seeds**: `app/seeds/` — demo data seeded on startup

### MCP (Model Context Protocol)

`app/mcp_server.py` exposes ops tools via FastMCP. Tools are defined in `app/services/ops_tools.py` as a registry of `ToolSpec` dataclasses with handlers wrapping K8s and observability clients.

### Configuration

Settings loaded via pydantic-settings from `backend/app/config/.env`. Key vars:
- `DATABASE_URL` — SQLite by default (`./data/kubemind.db`)
- `DEEPSEEK_AUTH_TOKEN` — LLM provider token
- `VECTOR_DB_HOST/PORT` — Milvus connection
- `PROMETHEUS_BASE_URL`, `LOKI_BASE_URL` — observability backends
- `KUBECONFIG_PATH` — path to kubeconfig

### Frontend Structure

React 18 + TypeScript + Vite. No CSS framework — uses custom CSS variables matching the dark sci-fi ops theme. Key pages:
- **ChatOps** — conversational ops interface with SSE streaming (`hooks/useChatOpsStream.ts`)
- **MCP** — tool/server management
- **Clusters** — K8s cluster overview
- **Alerts/Workflows/Knowledge** — CRUD management pages

All API calls go through `services/api.ts` which provides a typed client.

### Database

SQLite in development (auto-created at `backend/data/kubemind.db`). Tables created via `Base.metadata.create_all` on startup. Seeds run automatically on every boot.

## Key Patterns

- Backend uses sync SQLAlchemy (not async) with `SessionLocal` / `get_db` dependency
- LLM calls go through `app/services/llm.py` which wraps langchain-openai with DeepSeek config
- The ChatOps streaming endpoint yields SSE events via a generator in `services/chatops.py`
- Frontend uses no state management library — local component state only
- Vite proxy handles CORS in development; production needs a reverse proxy
