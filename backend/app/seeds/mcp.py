import json

from sqlalchemy.orm import Session
from app.models.mcp import MCPServer, Tool, SecurityPolicy

def seed_mcp_data(db: Session):
    # 检查是否已存在数据
    if db.query(MCPServer).first():
        return
    
    # 创建本地 MCP Server
    local_server = MCPServer(
        name="local-mcp",
        type="local",
        status="online",
        endpoint="http://localhost:8000",
        tools_count=6,
        metadata_json='{"description": "Local MCP Server"}'
    )
    db.add(local_server)
    db.flush()
    
    # 创建默认工具
    tools = [
        Tool(
            name="prometheus_query",
            category="监控",
            risk_level="low",
            enabled=True,
            timeout_ms=30000,
            retry=0,
            description="执行 Prometheus 查询",
            mcp_server_id=local_server.id,
            function_name="query_prometheus",
            parameters='{"query": "string", "time": "string"}'
        ),
        Tool(
            name="prometheus_range_query",
            category="监控",
            risk_level="low",
            enabled=True,
            timeout_ms=30000,
            retry=0,
            description="执行 Prometheus 范围查询",
            mcp_server_id=local_server.id,
            function_name="query_prometheus_range",
            parameters='{"query": "string", "start": "string", "end": "string", "step": "string"}'
        ),
        Tool(
            name="k8s_get_pods",
            category="容器",
            risk_level="low",
            enabled=True,
            timeout_ms=15000,
            retry=1,
            description="获取 Kubernetes Pod 列表",
            mcp_server_id=local_server.id,
            function_name="get_k8s_pods",
            parameters='{"namespace": "string"}'
        ),
        Tool(
            name="k8s_get_nodes",
            category="容器",
            risk_level="low",
            enabled=True,
            timeout_ms=15000,
            retry=1,
            description="获取 Kubernetes Node 列表",
            mcp_server_id=local_server.id,
            function_name="get_k8s_nodes",
            parameters='{}'
        ),
        Tool(
            name="loki_query",
            category="日志",
            risk_level="low",
            enabled=True,
            timeout_ms=30000,
            retry=0,
            description="执行 Loki 日志查询",
            mcp_server_id=local_server.id,
            function_name="query_loki",
            parameters='{"query": "string", "start": "string", "end": "string", "limit": "integer"}'
        ),
        Tool(
            name="k8s_describe_pod",
            category="容器",
            risk_level="medium",
            enabled=True,
            timeout_ms=15000,
            retry=1,
            description="获取 Pod 详细信息",
            mcp_server_id=local_server.id,
            function_name="describe_k8s_pod",
            parameters='{"name": "string", "namespace": "string"}'
        ),
    ]
    
    for tool in tools:
        db.add(tool)
    
    # 创建安全策略
    policies = [
        SecurityPolicy(
            name="default-policy",
            type="whitelist",
            enabled=True,
            description="默认安全策略",
            rules='{"deny_namespaces": ["kube-system"], "risk_level": "critical"}'
        ),
        SecurityPolicy(
            name="audit-logging",
            type="logging",
            enabled=True,
            description="审计日志策略",
            rules='{"log_all_calls": true, "log_sensitive_params": false}'
        ),
    ]
    
    for policy in policies:
        db.add(policy)
    
    db.commit()
    print("MCP seed data created successfully")


def sync_builtin_mcp_tools(db: Session):
    from app.services.ops_tools import build_ops_tool_registry

    server = db.query(MCPServer).filter(MCPServer.name == "kubemind-ops-mcp").first()
    if not server:
        server = MCPServer(
            name="kubemind-ops-mcp",
            type="local",
            status="online",
            endpoint="http://127.0.0.1:11000/mcp/",
            tools_count=0,
            metadata_json='{"description": "KubeMind FastMCP ops tool microservice"}',
        )
        db.add(server)
        db.flush()

    registry = build_ops_tool_registry()
    for spec in registry.values():
        tool = db.query(Tool).filter(Tool.name == spec.name).first()
        parameters = json.dumps(spec.parameters)
        if tool:
            tool.category = spec.category
            tool.risk_level = spec.risk_level
            tool.timeout_ms = spec.timeout_ms
            tool.retry = spec.retry
            tool.description = spec.description
            tool.function_name = spec.name
            tool.parameters = parameters
            tool.mcp_server_id = server.id
            continue
        db.add(
            Tool(
                name=spec.name,
                category=spec.category,
                risk_level=spec.risk_level,
                enabled=True,
                timeout_ms=spec.timeout_ms,
                retry=spec.retry,
                description=spec.description,
                mcp_server_id=server.id,
                function_name=spec.name,
                parameters=parameters,
            )
        )

    server.tools_count = len(registry)
    db.commit()
