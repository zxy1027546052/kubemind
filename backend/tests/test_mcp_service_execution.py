from app.models.mcp import SecurityPolicy, Tool
from app.core.database import Base
from app.services.mcp import MCPService
from app.services.ops_tools import ToolSpec
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_mcp_service_registers_builtin_tools_and_audits_success(db_session) -> None:
    db_session.add(
        Tool(
            name="sample_tool",
            category="ops",
            risk_level="low",
            enabled=True,
            timeout_ms=1000,
            retry=0,
            function_name="sample_tool",
            parameters="{}",
        )
    )
    db_session.commit()

    service = MCPService()
    service.register_tool_specs({
        "sample_tool": ToolSpec(
            name="sample_tool",
            category="ops",
            risk_level="low",
            description="Sample read-only tool",
            parameters={},
            handler=lambda namespace="default": {"namespace": namespace},
        )
    })

    result = service.execute_tool(
        db=db_session,
        tool_name="sample_tool",
        params={"namespace": "prod"},
        session_id="chat-1",
        trace_id="trace-1",
        namespace="prod",
    )

    assert result["success"] is True
    assert result["result"] == {"namespace": "prod"}
    records = service.list_audit_records(db_session, tool_name="sample_tool")
    assert len(records) == 1
    assert records[0].status == "success"
    assert records[0].namespace == "prod"


def test_mcp_service_blocks_denied_namespace_before_invoking_tool(db_session) -> None:
    db_session.add(
        Tool(
            name="sample_tool",
            category="ops",
            risk_level="low",
            enabled=True,
            timeout_ms=1000,
            retry=0,
            function_name="sample_tool",
            parameters="{}",
        )
    )
    db_session.add(
        SecurityPolicy(
            name="deny-kube-system",
            type="namespace",
            enabled=True,
            rules='{"deny_namespaces": ["kube-system"], "risk_level": "medium"}',
        )
    )
    db_session.commit()

    service = MCPService()
    service.register_tool_specs({
        "sample_tool": ToolSpec(
            name="sample_tool",
            category="ops",
            risk_level="low",
            description="Sample read-only tool",
            parameters={},
            handler=lambda namespace="default": {"namespace": namespace},
        )
    })

    result = service.execute_tool(
        db=db_session,
        tool_name="sample_tool",
        params={"namespace": "kube-system"},
        namespace="kube-system",
    )

    assert result["success"] is False
    assert "kube-system" in result["error"]
    records = service.list_audit_records(db_session, tool_name="sample_tool")
    assert len(records) == 1
    assert records[0].status == "error"


def test_audit_repository_filters_before_paginating(db_session) -> None:
    service = MCPService()
    for index in range(3):
        service._create_audit(
            db=db_session,
            tool_name="sample_tool",
            category="ops",
            session_id="target" if index == 2 else "other",
            status="success",
            duration_ms=1,
            params={},
            result_summary="ok",
            namespace="default",
        )
    db_session.commit()

    records = service.list_audit_records(db_session, session_id="target", limit=1)

    assert len(records) == 1
    assert records[0].session_id == "target"
