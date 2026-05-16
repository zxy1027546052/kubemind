import logging

from app.agents.state import OpsGraphState

logger = logging.getLogger(__name__)


def run_ops_graph(state: OpsGraphState) -> OpsGraphState:
    return run_ops_graph_with_db(state)


def run_ops_graph_with_db(state: OpsGraphState, db=None) -> OpsGraphState:
    """Run the ops pipeline via LangGraph. Logs a warning on degradation."""
    try:
        from app.agents.langgraph_flow import run_ops_graph_langgraph
        return run_ops_graph_langgraph(state, db=db)
    except ImportError:
        logger.warning("LangGraph not available, using direct execution")
    except Exception as e:
        logger.warning("LangGraph execution failed, falling back: %s", e)
        state["trace"].append({"agent": "Orchestrator", "message": f"LangGraph failed: {e}"})

    return _run_direct(state, db=db)


def _run_direct(state: OpsGraphState, db=None) -> OpsGraphState:
    """Direct execution without LangGraph: planner → ReAct (or legacy if no db)."""
    from app.agents.nodes import (
        diagnosis_agent,
        mcp_ops_agent,
        milvus_agent,
        observability_agent,
        planner_agent,
        retriever_agent,
    )

    state = planner_agent(state, db=db)

    if state["intent"] == "general_chat":
        return diagnosis_agent(state, db=db)

    if db is not None:
        from app.agents.react import ReactExecutor
        executor = ReactExecutor(db=db, state=state)
        state = executor.run()
        if state.get("llm_reply"):
            state["root_causes"].append({
                "title": "ReAct 分析完成",
                "confidence": 0.8,
                "evidence_count": len(state["evidence"]),
            })
            return state
        logger.warning("ReAct produced no reply, falling back to sequential")
        state["trace"].append({"agent": "Orchestrator", "message": "ReAct produced no reply"})

    state = retriever_agent(state)
    state = milvus_agent(state, db=db)
    state = observability_agent(state)
    if db is not None:
        state = mcp_ops_agent(state, db=db)
    state = diagnosis_agent(state, db=db)
    return state
