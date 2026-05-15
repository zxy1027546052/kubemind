from collections.abc import Callable

from app.agents.nodes import diagnosis_agent, mcp_ops_agent, milvus_agent, observability_agent, planner_agent, retriever_agent
from app.agents.state import OpsGraphState


AgentNode = Callable[[OpsGraphState], OpsGraphState]


MINIMAL_AGENT_GRAPH: list[AgentNode] = [
    planner_agent,
    retriever_agent,
    milvus_agent,
    observability_agent,
    diagnosis_agent,
]


def run_ops_graph(state: OpsGraphState) -> OpsGraphState:
    return run_ops_graph_with_db(state)


def run_ops_graph_with_db(state: OpsGraphState, db=None) -> OpsGraphState:
    """Run the ops pipeline. Uses LangGraph if available, falls back to sequential."""
    try:
        from app.agents.langgraph_flow import run_ops_graph_langgraph
        return run_ops_graph_langgraph(state, db=db)
    except Exception:
        return _run_sequential(state, db=db)


def _run_sequential(state: OpsGraphState, db=None) -> OpsGraphState:
    state = planner_agent(state, db=db)
    state = retriever_agent(state)
    state = milvus_agent(state, db=db)
    for node in (observability_agent,):
        state = node(state)
    if db is not None:
        state = mcp_ops_agent(state, db=db)
    state = diagnosis_agent(state, db=db)
    return state
