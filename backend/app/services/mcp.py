import asyncio
import json
import time
import requests
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.mcp import AuditRecord, MCPServer, SecurityPolicy, Tool
from app.repositories.mcp import (
    AuditRecordRepository,
    MCPServerRepository,
    SecurityPolicyRepository,
    ToolRepository,
)
from app.schemas.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    SecurityPolicyUpdate,
    ToolCreate,
    ToolUpdate,
)
from app.services.ops_tools import ToolSpec, build_ops_tool_registry


class MCPService:
    def __init__(self) -> None:
        self.server_repo = MCPServerRepository()
        self.tool_repo = ToolRepository()
        self.audit_repo = AuditRecordRepository()
        self.policy_repo = SecurityPolicyRepository()
        self._registered_tools: Dict[str, ToolSpec] = {}
        self.register_tool_specs(build_ops_tool_registry())

    def list_servers(self, db: Session) -> List[MCPServer]:
        return self.server_repo.get_all(db)

    def get_server(self, db: Session, id: int) -> Optional[MCPServer]:
        return self.server_repo.get_by_id(db, id)

    def create_server(self, db: Session, data: MCPServerCreate) -> MCPServer:
        existing = self.server_repo.get_by_name(db, data.name)
        if existing:
            raise ValueError(f"Server with name '{data.name}' already exists")
        return self.server_repo.create(db, data)

    def update_server(self, db: Session, id: int, data: MCPServerUpdate) -> Optional[MCPServer]:
        if data.name:
            existing = self.server_repo.get_by_name(db, data.name)
            if existing and existing.id != id:
                raise ValueError(f"Server with name '{data.name}' already exists")
        return self.server_repo.update(db, id, data)

    def delete_server(self, db: Session, id: int) -> bool:
        return self.server_repo.delete(db, id)

    def list_tools(self, db: Session, category: Optional[str] = None, risk_level: Optional[str] = None) -> List[Tool]:
        return self.tool_repo.get_all(db, category, risk_level)

    def get_tool(self, db: Session, id: int) -> Optional[Tool]:
        return self.tool_repo.get_by_id(db, id)

    def get_tool_by_name(self, db: Session, name: str) -> Optional[Tool]:
        return self.tool_repo.get_by_name(db, name)

    def create_tool(self, db: Session, data: ToolCreate) -> Tool:
        existing = self.tool_repo.get_by_name(db, data.name)
        if existing:
            raise ValueError(f"Tool with name '{data.name}' already exists")
        return self.tool_repo.create(db, data)

    def update_tool(self, db: Session, id: int, data: ToolUpdate) -> Optional[Tool]:
        if data.name:
            existing = self.tool_repo.get_by_name(db, data.name)
            if existing and existing.id != id:
                raise ValueError(f"Tool with name '{data.name}' already exists")
        return self.tool_repo.update(db, id, data)

    def delete_tool(self, db: Session, id: int) -> bool:
        return self.tool_repo.delete(db, id)

    def register_tool(self, name: str, func, category: str = "general", risk_level: str = "low") -> None:
        self._registered_tools[name] = ToolSpec(
            name=name,
            category=category,
            risk_level=risk_level,
            description="Runtime registered tool",
            parameters={},
            handler=func,
        )

    def register_tool_specs(self, specs: Dict[str, ToolSpec]) -> None:
        self._registered_tools.update(specs)

    def get_registered_tool(self, name: str) -> Optional[ToolSpec]:
        return self._registered_tools.get(name)

    def execute_tool(
        self,
        db: Session,
        tool_name: str,
        params: dict | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
        namespace: str = "",
    ) -> Dict[str, Any]:
        start_time = time.time()
        params = params or {}
        tool: Tool | None = None

        try:
            tool = self.get_tool_by_name(db, tool_name)
            if not tool:
                raise ValueError(f"Tool '{tool_name}' does not exist")
            if not tool.enabled:
                raise ValueError(f"Tool '{tool_name}' is disabled")

            self._check_policy(db, tool, namespace)
            registered = self.get_registered_tool(tool_name)
            if not registered:
                raise ValueError(f"Tool '{tool_name}' has no registered handler")

            try:
                result = self._call_with_retries(
                    registered.handler,
                    params,
                    timeout=tool.timeout_ms / 1000,
                    retry=tool.retry,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Tool '{tool_name}' timed out")

            duration_ms = int((time.time() - start_time) * 1000)
            audit_record = self._create_audit(
                db=db,
                tool_name=tool_name,
                category=tool.category,
                session_id=session_id,
                trace_id=trace_id,
                status="success",
                duration_ms=duration_ms,
                params=params,
                result_summary=str(result)[:500],
                namespace=namespace,
            )

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
                "audit_id": audit_record.id if audit_record else None,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            self._create_audit(
                db=db,
                tool_name=tool_name,
                category=tool.category if tool else "unknown",
                session_id=session_id,
                trace_id=trace_id,
                status="error",
                duration_ms=duration_ms,
                params=params,
                result_summary="",
                error_message=error_msg,
                namespace=namespace,
            )
            return {
                "success": False,
                "error": error_msg,
                "duration_ms": duration_ms,
                "audit_id": None,
            }

    def _call_with_retries(self, func, params: dict, timeout: float, retry: int) -> Any:
        attempts = max(retry, 0) + 1
        last_error: Exception | None = None
        for _attempt in range(attempts):
            try:
                result = func(**params)
                if asyncio.iscoroutine(result):
                    return asyncio.run(asyncio.wait_for(result, timeout=timeout))
                return result
            except Exception as e:
                last_error = e
        if last_error:
            raise last_error
        raise RuntimeError("Tool execution failed")

    def _check_policy(self, db: Session, tool: Tool, namespace: str) -> None:
        policies = self.policy_repo.get_all(db)
        for policy in policies:
            if not policy.enabled:
                continue
            try:
                rules = json.loads(policy.rules)
                if "deny_namespaces" in rules and namespace in rules["deny_namespaces"]:
                    raise ValueError(f"Namespace '{namespace}' is blocked by policy '{policy.name}'")
                if "risk_level" in rules:
                    allowed_risk = rules["risk_level"]
                    risk_order = ["low", "medium", "high", "critical"]
                    if risk_order.index(tool.risk_level) > risk_order.index(allowed_risk):
                        raise ValueError(f"Tool risk level '{tool.risk_level}' exceeds allowed level")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                if isinstance(e, ValueError):
                    raise
                continue

    def _create_audit(self, db: Session, **kwargs) -> AuditRecord:
        kwargs["params"] = json.dumps(kwargs.get("params", {}))
        return self.audit_repo.create(db, **kwargs)

    def list_audit_records(
        self,
        db: Session,
        tool_name: Optional[str] = None,
        session_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[AuditRecord]:
        return self.audit_repo.get_all(db, tool_name, session_id, offset, limit)

    def get_audit_record(self, db: Session, id: int) -> Optional[AuditRecord]:
        return self.audit_repo.get_by_id(db, id)

    def list_policies(self, db: Session) -> List[SecurityPolicy]:
        return self.policy_repo.get_all(db)

    def get_policy(self, db: Session, id: int) -> Optional[SecurityPolicy]:
        return self.policy_repo.get_by_id(db, id)

    def update_policy(self, db: Session, id: int, data: SecurityPolicyUpdate) -> Optional[SecurityPolicy]:
        return self.policy_repo.update(db, id, data)

    def test_server_connection(self, endpoint: str) -> Dict[str, Any]:
        """测试 MCP 服务器连接"""
        start_time = time.time()
        try:
            res = requests.get(endpoint, timeout=10)
            response_time_ms = int((time.time() - start_time) * 1000)
            return {
                "success": res.ok,
                "status_code": res.status_code,
                "response_time_ms": response_time_ms,
                "message": f"HTTP {res.status_code} - {res.reason}" if res.ok else f"HTTP {res.status_code} - {res.reason}",
                "error": None,
            }
        except requests.exceptions.RequestException as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": response_time_ms,
                "message": str(e),
                "error": str(e),
            }
