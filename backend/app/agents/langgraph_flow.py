"""LangGraph-based agent orchestration with conditional edges.

Replaces the sequential run_ops_graph_with_db with a proper StateGraph
that supports conditional routing based on intent.
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
from app.agents.state import OpsGraphState


def _wrap_planner(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        return planner_agent(state, db=db)
    return node


def _wrap_retriever(state: OpsGraphState) -> OpsGraphState:
    return retriever_agent(state)


def _wrap_milvus(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        return milvus_agent(state, db=db)
    return node


def _wrap_observability(state: OpsGraphState) -> OpsGraphState:
    return observability_agent(state)


def _wrap_mcp_ops(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        return mcp_ops_agent(state, db=db)
    return node


def _wrap_diagnosis(db=None):
    def node(state: OpsGraphState) -> OpsGraphState:
        return diagnosis_agent(state, db=db)
    return node


def _route_after_planner(state: OpsGraphState) -> str:
    """Conditional edge: skip heavy agents for general chat."""
    if state["intent"] == "general_chat":
        return "diagnosis"
    return "retriever"


def _route_after_observability(state: OpsGraphState) -> str:
    """Conditional edge: only run MCP tools for actionable intents."""
    if state["intent"] in {"diagnose_issue", "query_metric", "query_logs", "query_cluster"}:
        return "mcp_ops"
    return "diagnosis"


def build_ops_graph(db=None) -> Any:
    """Build and compile the LangGraph StateGraph for the ops pipeline."""
    graph = StateGraph(OpsGraphState)

    graph.add_node("planner", _wrap_planner(db))
    graph.add_node("retriever", _wrap_retriever)
    graph.add_node("milvus", _wrap_milvus(db))
    graph.add_node("observability", _wrap_observability)
    graph.add_node("mcp_ops", _wrap_mcp_ops(db))
    graph.add_node("diagnosis", _wrap_diagnosis(db))

    graph.set_entry_point("planner")

    graph.add_conditional_edges("planner", _route_after_planner, {
        "retriever": "retriever",
        "diagnosis": "diagnosis",
    })

    graph.add_edge("retriever", "milvus")
    graph.add_edge("milvus", "observability")

    graph.add_conditional_edges("observability", _route_after_observability, {
        "mcp_ops": "mcp_ops",
        "diagnosis": "diagnosis",
    })

    graph.add_edge("mcp_ops", "diagnosis")
    graph.add_edge("diagnosis", END)

    return graph.compile()


def run_ops_graph_langgraph(state: OpsGraphState, db=None) -> OpsGraphState:
    """Execute the full ops pipeline via LangGraph."""
    compiled = build_ops_graph(db=db)
    result = compiled.invoke(state)
    return result
