from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, desc, func

from app.models.mcp import MCPServer, Tool, AuditRecord, SecurityPolicy
from app.schemas.mcp import MCPServerCreate, MCPServerUpdate, ToolCreate, ToolUpdate, SecurityPolicyUpdate

class MCPServerRepository:
    def get_all(self, db: Session) -> List[MCPServer]:
        result = db.execute(select(MCPServer))
        return result.scalars().all()

    def get_by_id(self, db: Session, id: int) -> Optional[MCPServer]:
        result = db.execute(select(MCPServer).where(MCPServer.id == id))
        return result.scalars().first()

    def get_by_name(self, db: Session, name: str) -> Optional[MCPServer]:
        result = db.execute(select(MCPServer).where(MCPServer.name == name))
        return result.scalars().first()

    def create(self, db: Session, data: MCPServerCreate) -> MCPServer:
        server = MCPServer(
            name=data.name,
            type=data.type,
            endpoint=data.endpoint,
            metadata_json=data.metadata_json
        )
        db.add(server)
        db.flush()
        db.refresh(server)
        return server

    def update(self, db: Session, id: int, data: MCPServerUpdate) -> Optional[MCPServer]:
        server = self.get_by_id(db, id)
        if not server:
            return None

        if data.name is not None:
            server.name = data.name
        if data.type is not None:
            server.type = data.type
        if data.endpoint is not None:
            server.endpoint = data.endpoint
        if data.status is not None:
            server.status = data.status
        if data.metadata_json is not None:
            server.metadata_json = data.metadata_json

        db.flush()
        db.refresh(server)
        return server

    def delete(self, db: Session, id: int) -> bool:
        server = self.get_by_id(db, id)
        if not server:
            return False
        db.delete(server)
        db.flush()
        return True

    def count(self, db: Session) -> int:
        result = db.execute(select(func.count(MCPServer.id)))
        return result.scalar_one()

class ToolRepository:
    def get_all(self, db: Session, category: Optional[str] = None, risk_level: Optional[str] = None) -> List[Tool]:
        query = select(Tool)
        if category:
            query = query.where(Tool.category == category)
        if risk_level:
            query = query.where(Tool.risk_level == risk_level)
        result = db.execute(query)
        return result.scalars().all()

    def get_by_id(self, db: Session, id: int) -> Optional[Tool]:
        result = db.execute(select(Tool).where(Tool.id == id))
        return result.scalars().first()

    def get_by_name(self, db: Session, name: str) -> Optional[Tool]:
        result = db.execute(select(Tool).where(Tool.name == name))
        return result.scalars().first()

    def create(self, db: Session, data: ToolCreate) -> Tool:
        tool = Tool(
            name=data.name,
            category=data.category,
            risk_level=data.risk_level,
            timeout_ms=data.timeout_ms,
            retry=data.retry,
            description=data.description,
            mcp_server_id=data.mcp_server_id,
            function_name=data.function_name,
            parameters=data.parameters
        )
        db.add(tool)
        db.flush()
        db.refresh(tool)
        return tool

    def update(self, db: Session, id: int, data: ToolUpdate) -> Optional[Tool]:
        tool = self.get_by_id(db, id)
        if not tool:
            return None

        if data.name is not None:
            tool.name = data.name
        if data.category is not None:
            tool.category = data.category
        if data.risk_level is not None:
            tool.risk_level = data.risk_level
        if data.enabled is not None:
            tool.enabled = data.enabled
        if data.timeout_ms is not None:
            tool.timeout_ms = data.timeout_ms
        if data.retry is not None:
            tool.retry = data.retry
        if data.description is not None:
            tool.description = data.description
        if data.parameters is not None:
            tool.parameters = data.parameters

        db.flush()
        db.refresh(tool)
        return tool

    def delete(self, db: Session, id: int) -> bool:
        tool = self.get_by_id(db, id)
        if not tool:
            return False
        db.delete(tool)
        db.flush()
        return True

    def count(self, db: Session) -> int:
        result = db.execute(select(func.count(Tool.id)))
        return result.scalar_one()

class AuditRecordRepository:
    def get_all(self, db: Session, tool_name: Optional[str] = None, session_id: Optional[str] = None, offset: int = 0, limit: int = 100) -> List[AuditRecord]:
        query = select(AuditRecord)
        if tool_name:
            query = query.where(AuditRecord.tool_name == tool_name)
        if session_id:
            query = query.where(AuditRecord.session_id == session_id)
        query = query.order_by(desc(AuditRecord.created_at)).offset(offset).limit(limit)
        result = db.execute(query)
        return result.scalars().all()

    def get_by_id(self, db: Session, id: int) -> Optional[AuditRecord]:
        result = db.execute(select(AuditRecord).where(AuditRecord.id == id))
        return result.scalars().first()

    def create(self, db: Session, **kwargs) -> AuditRecord:
        record = AuditRecord(**kwargs)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def count(self, db: Session) -> int:
        result = db.execute(select(func.count(AuditRecord.id)))
        return result.scalar_one()

class SecurityPolicyRepository:
    def get_all(self, db: Session) -> List[SecurityPolicy]:
        result = db.execute(select(SecurityPolicy))
        return result.scalars().all()

    def get_by_id(self, db: Session, id: int) -> Optional[SecurityPolicy]:
        result = db.execute(select(SecurityPolicy).where(SecurityPolicy.id == id))
        return result.scalars().first()

    def get_by_name(self, db: Session, name: str) -> Optional[SecurityPolicy]:
        result = db.execute(select(SecurityPolicy).where(SecurityPolicy.name == name))
        return result.scalars().first()

    def create(self, db: Session, name: str, type: str, enabled: bool = True, description: str = None, rules: str = "{}") -> SecurityPolicy:
        policy = SecurityPolicy(
            name=name,
            type=type,
            enabled=enabled,
            description=description,
            rules=rules
        )
        db.add(policy)
        db.flush()
        db.refresh(policy)
        return policy

    def update(self, db: Session, id: int, data: SecurityPolicyUpdate) -> Optional[SecurityPolicy]:
        policy = self.get_by_id(db, id)
        if not policy:
            return None

        if data.name is not None:
            policy.name = data.name
        if data.type is not None:
            policy.type = data.type
        if data.enabled is not None:
            policy.enabled = data.enabled
        if data.description is not None:
            policy.description = data.description
        if data.rules is not None:
            policy.rules = data.rules

        db.flush()
        db.refresh(policy)
        return policy

    def delete(self, db: Session, id: int) -> bool:
        policy = self.get_by_id(db, id)
        if not policy:
            return False
        db.delete(policy)
        db.flush()
        return True
