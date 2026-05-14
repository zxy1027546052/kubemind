import re

from sqlalchemy.orm import Session

NAMESPACE_PATTERN = re.compile(r"\b(default|prod|dev|test|staging|kube-system)\b", re.IGNORECASE)
WORKLOAD_PATTERN = re.compile(r"\b([a-z][a-z0-9-]*(?:api|server|service|worker|gateway)[a-z0-9-]*)\b", re.IGNORECASE)

_GENERAL_CHAT_KEYWORDS = (
    "你好", "你是谁", "什么模型", "模型是", "哪个模型", "版本",
    "能做什么", "有什么功能", "帮助", "help", "谢谢", "thank",
    "hello", "hi", "hey", "who are you", "what are you",
    "what can you do", "how are you",
)

_FAULT_KEYWORDS = ("分析", "诊断", "故障", "异常", "超时", "排查问题", "出问题")

_VALID_INTENTS = frozenset({
    "general_chat", "query_metric", "query_logs", "diagnose_issue",
    "search_runbook", "create_workflow", "query_cluster",
})


def _classify_by_keywords(message: str) -> str | None:
    """Fast keyword-based classification. Returns None if no confident match."""
    text = message.lower()

    if any(kw in text for kw in _GENERAL_CHAT_KEYWORDS):
        return "general_chat"
    if any(keyword in text for keyword in ("生成排查流程", "创建流程", "create workflow")):
        return "create_workflow"
    if any(keyword in text for keyword in ("milvus", "向量库", "向量数据库", "vector")):
        return "search_runbook"
    if any(keyword in text for keyword in ("runbook", "手册", "处理手册", "知识库")):
        return "search_runbook"
    if any(keyword in text for keyword in ("日志", "log", "错误日志", "错误", "error")):
        if any(kw in text for kw in _FAULT_KEYWORDS):
            return "diagnose_issue"
        return "query_logs"
    if any(keyword in text for keyword in ("cpu", "内存", "memory", "指标", "metric")):
        return "query_metric"
    if any(kw in text for kw in _FAULT_KEYWORDS):
        return "diagnose_issue"
    if any(keyword in text for keyword in ("集群", "节点", "pod")):
        return "query_cluster"

    return None


def _classify_by_llm(message: str, db: Session) -> str | None:
    """LLM-based intent classification fallback."""
    try:
        from app.services.llm import chat_completion

        prompt = (
            "你是意图分类器。将用户消息分类为以下意图之一：\n"
            "query_metric, query_logs, diagnose_issue, search_runbook, "
            "create_workflow, query_cluster, general_chat\n\n"
            "规则：\n"
            "- 如果用户在闲聊、问候、询问系统信息，返回 general_chat\n"
            "- 如果用户想查看指标数据，返回 query_metric\n"
            "- 如果用户想查看日志，返回 query_logs\n"
            "- 如果用户描述了故障或想排查问题，返回 diagnose_issue\n"
            "- 如果用户想找处理手册或文档，返回 search_runbook\n"
            "- 如果用户想创建流程，返回 create_workflow\n"
            "- 如果用户想查看集群/节点/Pod状态，返回 query_cluster\n\n"
            "只输出意图名称，不要其他文字。\n\n"
            f"用户消息：{message}"
        )
        result = chat_completion(
            db,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=32,
        )
        intent = result.strip().lower().replace('"', "").replace("'", "")
        if intent in _VALID_INTENTS:
            return intent
    except Exception:
        pass
    return None


def classify_intent(message: str, db: Session | None = None) -> str:
    """Hybrid intent classification: keywords first, LLM fallback."""
    result = _classify_by_keywords(message)
    if result is not None:
        return result

    if db is not None:
        llm_result = _classify_by_llm(message, db)
        if llm_result is not None:
            return llm_result

    return "general_chat"


def extract_entities(message: str) -> dict[str, str]:
    entities: dict[str, str] = {}
    namespace_match = NAMESPACE_PATTERN.search(message)
    workload_match = WORKLOAD_PATTERN.search(message)

    if namespace_match:
        entities["namespace"] = namespace_match.group(1).lower()
    if workload_match:
        entities["workload"] = workload_match.group(1)
    if "cpu" in message.lower():
        entities["metric"] = "cpu"
    if "内存" in message or "memory" in message.lower():
        entities["metric"] = "memory"
    return entities
