from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

# MCPServer schemas
class MCPServerBase(BaseModel):
    name: str = Field(..., description="服务器名称")
    type: str = Field("local", description="服务器类型", pattern="^(local|remote)$")
    endpoint: str = Field(..., description="服务器端点地址")
    metadata_json: Optional[str] = Field("{}", description="元数据 JSON")

class MCPServerCreate(MCPServerBase):
    pass

class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, description="服务器名称")
    type: Optional[str] = Field(None, description="服务器类型", pattern="^(local|remote)$")
    endpoint: Optional[str] = Field(None, description="服务器端点地址")
    status: Optional[str] = Field(None, description="服务器状态")
    metadata_json: Optional[str] = Field(None, description="元数据 JSON")

class MCPServerResponse(MCPServerBase):
    id: int
    status: str
    tools_count: int
    last_heartbeat: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MCPServerListResponse(BaseModel):
    total: int
    items: List[MCPServerResponse]

# Tool schemas
class ToolBase(BaseModel):
    name: str = Field(..., description="工具名称")
    category: str = Field(..., description="工具分类")
    risk_level: str = Field("low", description="风险等级", pattern="^(low|medium|high|critical)$")
    timeout_ms: int = Field(30000, description="超时时间（毫秒）")
    retry: int = Field(0, description="重试次数")
    description: Optional[str] = Field(None, description="工具描述")
    function_name: str = Field(..., description="函数名称")
    mcp_server_id: Optional[int] = Field(None, description="关联的 MCP Server ID")
    parameters: Optional[str] = Field("{}", description="参数定义 JSON")

class ToolCreate(ToolBase):
    pass

class ToolUpdate(BaseModel):
    name: Optional[str] = Field(None, description="工具名称")
    category: Optional[str] = Field(None, description="工具分类")
    risk_level: Optional[str] = Field(None, description="风险等级")
    enabled: Optional[bool] = Field(None, description="是否启用")
    timeout_ms: Optional[int] = Field(None, description="超时时间")
    retry: Optional[int] = Field(None, description="重试次数")
    description: Optional[str] = Field(None, description="工具描述")
    parameters: Optional[str] = Field(None, description="参数定义 JSON")

class ToolResponse(ToolBase):
    id: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ToolListResponse(BaseModel):
    total: int
    items: List[ToolResponse]

# Tool Execute
class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="工具名称")
    params: Optional[Dict[str, Any]] = Field({}, description="工具参数")
    session_id: Optional[str] = Field(None, description="会话 ID")
    trace_id: Optional[str] = Field(None, description="追踪 ID")
    namespace: Optional[str] = Field("", description="命名空间")

class ToolExecuteResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    duration_ms: int = Field(0, description="执行耗时（毫秒）")
    audit_id: Optional[int] = Field(None, description="审计记录 ID")

# Audit schemas
class AuditRecordResponse(BaseModel):
    id: int
    tool_name: str
    category: str
    caller: str
    session_id: Optional[str]
    trace_id: Optional[str]
    status: str
    duration_ms: int
    params: str
    result_summary: str
    error_message: str
    namespace: str
    created_at: datetime

    class Config:
        from_attributes = True

class AuditListResponse(BaseModel):
    total: int
    items: List[AuditRecordResponse]

# Security Policy schemas
class SecurityPolicyBase(BaseModel):
    name: str = Field(..., description="策略名称")
    type: str = Field(..., description="策略类型")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="策略描述")
    rules: str = Field("{}", description="策略规则 JSON")

class SecurityPolicyCreate(SecurityPolicyBase):
    pass

class SecurityPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, description="策略名称")
    type: Optional[str] = Field(None, description="策略类型")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="策略描述")
    rules: Optional[str] = Field(None, description="策略规则 JSON")

class SecurityPolicyResponse(SecurityPolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PolicyListResponse(BaseModel):
    total: int
    items: List[SecurityPolicyResponse]