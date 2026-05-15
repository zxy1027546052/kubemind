import asyncio
import time
import json
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.models.mcp import MCPServer, Tool, AuditRecord, SecurityPolicy
from app.schemas.mcp import MCPServerCreate, MCPServerUpdate, ToolCreate, ToolUpdate, ToolExecuteRequest, SecurityPolicyUpdate
from app.repositories.mcp import MCPServerRepository, ToolRepository, AuditRecordRepository, SecurityPolicyRepository

class MCPService:
    def __init__(self):
        self.server_repo = MCPServerRepository()
        self.tool_repo = ToolRepository()
        self.audit_repo = AuditRecordRepository()
        self.policy_repo = SecurityPolicyRepository()
        self._registered_tools: Dict[str, dict] = {}

    # Server Management
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

    # Tool Management
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

    # Tool Registration & Execution
    def register_tool(self, name: str, func, category: str = "general", risk_level: str = "low"):
        self._registered_tools[name] = {
            "func": func,
            "category": category,
            "risk_level": risk_level
        }

    def get_registered_tool(self, name: str) -> Optional[dict]:
        return self._registered_tools.get(name)

    def execute_tool(self, db: Session, tool_name: str, params: dict = None,
                     session_id: str = None, trace_id: str = None, namespace: str = "") -> Dict[str, Any]:
        start_time = time.time()
        params = params or {}

        try:
            tool = self.get_tool_by_name(db, tool_name)
            if not tool:
                raise ValueError(f"工具 {tool_name} 不存在")

            if not tool.enabled:
                raise ValueError(f"工具 {tool_name} 已禁用")

            self._check_policy(db, tool, namespace)

            registered = self.get_registered_tool(tool_name)
            if not registered:
                raise ValueError(f"工具 {tool_name} 未注册执行函数")

            func = registered["func"]
            timeout = tool.timeout_ms / 1000

            try:
                result = func(**params)
                if asyncio.iscoroutine(result):
                    result = asyncio.run(asyncio.wait_for(result, timeout=timeout))
            except asyncio.TimeoutError:
                raise TimeoutError(f"工具 {tool_name} 执行超时")

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
                namespace=namespace
            )

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
                "audit_id": audit_record.id if audit_record else None
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            self._create_audit(
                db=db,
                tool_name=tool_name,
                category="unknown",
                session_id=session_id,
                trace_id=trace_id,
                status="error",
                duration_ms=duration_ms,
                params=params,
                result_summary="",
                error_message=error_msg,
                namespace=namespace
            )
            return {
                "success": False,
                "error": error_msg,
                "duration_ms": duration_ms,
                "audit_id": None
            }

    def _check_policy(self, db: Session, tool: Tool, namespace: str):
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
            except (json.JSONDecodeError, KeyError):
                continue

    def _create_audit(self, db: Session, **kwargs) -> AuditRecord:
        kwargs["params"] = json.dumps(kwargs.get("params", {}))
        return self.audit_repo.create(db, **kwargs)

    # Audit Records
    def list_audit_records(self, db: Session, tool_name: Optional[str] = None,
                           session_id: Optional[str] = None, offset: int = 0, limit: int = 100) -> List[AuditRecord]:
        return self.audit_repo.get_all(db, tool_name, session_id, offset, limit)

    def get_audit_record(self, db: Session, id: int) -> Optional[AuditRecord]:
        return self.audit_repo.get_by_id(db, id)

    # Security Policies
    def list_policies(self, db: Session) -> List[SecurityPolicy]:
        return self.policy_repo.get_all(db)

    def get_policy(self, db: Session, id: int) -> Optional[SecurityPolicy]:
        return self.policy_repo.get_by_id(db, id)

    def update_policy(self, db: Session, id: int, data: SecurityPolicyUpdate) -> Optional[SecurityPolicy]:
        return self.policy_repo.update(db, id, data)