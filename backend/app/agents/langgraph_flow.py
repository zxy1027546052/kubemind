"""LangGraph-based agent orchestration with ReAct executor.

The graph routes: planner → [general_chat → diagnosis] OR [react_executor → diagnosis]
The ReAct executor autonomously decides which tools to call and when to stop.
When db is None, falls back to the legacy sequential nodes.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    diagnosis_agent,
    mcp_ops_agent,
    milvus_agent,
    observability_agent,
    planner_agent,
    retriever_agent,
)
from app.agents.react import ReactExecutor
from app.agents.state import OpsGraphState
from app.services.mcp import MCPService


def _wrap_planner(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        return planner_agent(state, db=db)
    return node


def _wrap_react_executor(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        if db is None:
            return state
        executor = ReactExecutor(db=db, state=state)
        return executor.run()
    return node


def _wrap_legacy_sequential(db=None):
    """Legacy sequential pipeline for when db is None or ReAct is unavailable."""
    def node(state: OpsGraphState) -> OpsGraphState:
        state = retriever_agent(state)
        state = milvus_agent(state, db=db)
        state = observability_agent(state)
        if db is not None:
            state = mcp_ops_agent(state, db=db)
        return state
    return node


def _wrap_diagnosis(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        if state.get("llm_reply"):
            state["root_causes"].append({
                "title": "ReAct 分析完成",
                "confidence": 0.8,
                "evidence_count": len(state["evidence"]),
            })
            state["trace"].append({"agent": "DiagnosisAgent", "message": "using ReAct reply"})
            return state
        return diagnosis_agent(state, db=db)
    return node


def _route_after_planner(state: OpsGraphState) -> str:
    if state["intent"] == "general_chat":
        return "diagnosis"
    return "executor"


def build_ops_graph(db=None) -> Any:
    graph = StateGraph(OpsGraphState)

    graph.add_node("planner", _wrap_planner(db))
    if db is not None:
        graph.add_node("executor", _wrap_react_executor(db))
    else:
        graph.add_node("executor", _wrap_legacy_sequential(db))
    graph.add_node("diagnosis", _wrap_diagnosis(db))

    graph.set_entry_point("planner")

    graph.add_conditional_edges("planner", _route_after_planner, {
        "executor": "executor",
        "diagnosis": "diagnosis",
    })

    graph.add_edge("executor", "diagnosis")
    graph.add_edge("diagnosis", END)

    return graph.compile()


def run_ops_graph_langgraph(state: OpsGraphState, db=None) -> OpsGraphState:
    compiled = build_ops_graph(db=db)
    result = compiled.invoke(state)
    return result
