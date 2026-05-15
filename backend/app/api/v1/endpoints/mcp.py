from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.schemas.mcp import (
    MCPServerResponse, MCPServerCreate, MCPServerUpdate, MCPServerListResponse,
    ToolResponse, ToolCreate, ToolUpdate, ToolListResponse,
    ToolExecuteRequest, ToolExecuteResponse,
    AuditRecordResponse, AuditListResponse,
    SecurityPolicyResponse, SecurityPolicyUpdate, PolicyListResponse
)
from app.services.mcp import MCPService

router = APIRouter()
mcp_service = MCPService()

@router.get("/mcp/servers", response_model=MCPServerListResponse)
def list_servers(db: Session = Depends(get_db)):
    servers = mcp_service.list_servers(db)
    return {"total": len(servers), "items": servers}

@router.get("/mcp/servers/{id}", response_model=MCPServerResponse)
def get_server(id: int, db: Session = Depends(get_db)):
    server = mcp_service.get_server(db, id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@router.post("/mcp/servers", response_model=MCPServerResponse, status_code=201)
def create_server(data: MCPServerCreate, db: Session = Depends(get_db)):
    try:
        server = mcp_service.create_server(db, data)
        db.commit()
        return server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/mcp/servers/{id}", response_model=MCPServerResponse)
def update_server(id: int, data: MCPServerUpdate, db: Session = Depends(get_db)):
    try:
        server = mcp_service.update_server(db, id, data)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        db.commit()
        return server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/mcp/servers/{id}")
def delete_server(id: int, db: Session = Depends(get_db)):
    success = mcp_service.delete_server(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Server not found")
    db.commit()
    return {"message": "Server deleted successfully"}

@router.get("/mcp/tools", response_model=ToolListResponse)
def list_tools(
    category: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    tools = mcp_service.list_tools(db, category, risk_level)
    return {"total": len(tools), "items": tools}

@router.get("/mcp/tools/{id}", response_model=ToolResponse)
def get_tool(id: int, db: Session = Depends(get_db)):
    tool = mcp_service.get_tool(db, id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@router.post("/mcp/tools", response_model=ToolResponse, status_code=201)
def create_tool(data: ToolCreate, db: Session = Depends(get_db)):
    try:
        tool = mcp_service.create_tool(db, data)
        db.commit()
        return tool
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/mcp/tools/{id}", response_model=ToolResponse)
def update_tool(id: int, data: ToolUpdate, db: Session = Depends(get_db)):
    try:
        tool = mcp_service.update_tool(db, id, data)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        db.commit()
        return tool
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/mcp/tools/{id}")
def delete_tool(id: int, db: Session = Depends(get_db)):
    success = mcp_service.delete_tool(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Tool not found")
    db.commit()
    return {"message": "Tool deleted successfully"}

@router.post("/mcp/tools/execute", response_model=ToolExecuteResponse)
def execute_tool(data: ToolExecuteRequest, db: Session = Depends(get_db)):
    result = mcp_service.execute_tool(
        db=db,
        tool_name=data.tool_name,
        params=data.params,
        session_id=data.session_id,
        trace_id=data.trace_id,
        namespace=data.namespace
    )
    db.commit()
    return result

@router.get("/mcp/audit", response_model=AuditListResponse)
def list_audit_records(
    tool_name: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    records = mcp_service.list_audit_records(db, tool_name, session_id, offset, limit)
    total = mcp_service.audit_repo.count(db)
    return {"total": total, "items": records}

@router.get("/mcp/audit/{id}", response_model=AuditRecordResponse)
def get_audit_record(id: int, db: Session = Depends(get_db)):
    record = mcp_service.get_audit_record(db, id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return record

@router.get("/mcp/policies", response_model=PolicyListResponse)
def list_policies(db: Session = Depends(get_db)):
    policies = mcp_service.list_policies(db)
    return {"total": len(policies), "items": policies}

@router.get("/mcp/policies/{id}", response_model=SecurityPolicyResponse)
def get_policy(id: int, db: Session = Depends(get_db)):
    policy = mcp_service.get_policy(db, id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.patch("/mcp/policies/{id}", response_model=SecurityPolicyResponse)
def update_policy(id: int, data: SecurityPolicyUpdate, db: Session = Depends(get_db)):
    policy = mcp_service.update_policy(db, id, data)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.commit()
    return policy