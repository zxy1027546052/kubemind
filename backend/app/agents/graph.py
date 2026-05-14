from collections.abc import Callable

from app.agents.nodes import diagnosis_agent, milvus_agent, observability_agent, planner_agent, retriever_agent
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
    state = planner_agent(state, db=db)
    state = retriever_agent(state)
    state = milvus_agent(state, db=db)
    for node in (observability_agent,):
        state = node(state)
    state = diagnosis_agent(state, db=db)
    return state
