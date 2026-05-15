from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class MCPServer(Base):
    __tablename__ = "mcp_servers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False, default="local")
    status = Column(String(20), nullable=False, default="offline")
    endpoint = Column(String(255), nullable=False)
    tools_count = Column(Integer, default=0)
    last_heartbeat = Column(DateTime, nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    tools = relationship("Tool", back_populates="mcp_server")

class Tool(Base):
    __tablename__ = "mcp_tools"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False, default="low")
    enabled = Column(Boolean, nullable=False, default=True)
    timeout_ms = Column(Integer, nullable=False, default=30000)
    retry = Column(Integer, nullable=False, default=0)
    description = Column(Text)
    mcp_server_id = Column(Integer, ForeignKey("mcp_servers.id"))
    function_name = Column(String(200), nullable=False)
    parameters = Column(Text, default="{}")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    mcp_server = relationship("MCPServer", back_populates="tools")
    audit_records = relationship("AuditRecord", back_populates="tool")

class AuditRecord(Base):
    __tablename__ = "mcp_audit_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(100), nullable=False)
    category = Column(String(50))
    caller = Column(String(100), default="system")
    session_id = Column(String(64))
    trace_id = Column(String(64))
    status = Column(String(20), nullable=False)
    duration_ms = Column(Integer)
    params = Column(Text, default="{}")
    result_summary = Column(Text)
    error_message = Column(Text)
    namespace = Column(String(100), default="")
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    tool_id = Column(Integer, ForeignKey("mcp_tools.id"))
    tool = relationship("Tool", back_populates="audit_records")

class SecurityPolicy(Base):
    __tablename__ = "mcp_security_policies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    description = Column(Text)
    rules = Column(Text, default="{}")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())