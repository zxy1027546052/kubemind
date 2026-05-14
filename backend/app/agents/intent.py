import re


NAMESPACE_PATTERN = re.compile(r"\b(default|prod|dev|test|staging|kube-system)\b", re.IGNORECASE)
WORKLOAD_PATTERN = re.compile(r"\b([a-z][a-z0-9-]*(?:api|server|service|worker|gateway)[a-z0-9-]*)\b", re.IGNORECASE)

_GENERAL_CHAT_KEYWORDS = (
    "你好", "你是谁", "什么模型", "模型是", "哪个模型", "版本",
    "能做什么", "有什么功能", "帮助", "help", "谢谢", "thank",
    "hello", "hi", "hey", "who are you", "what are you",
    "what can you do", "how are you",
)

_FAULT_KEYWORDS = ("分析", "诊断", "故障", "异常", "超时", "排查问题", "出问题")


def classify_intent(message: str) -> str:
    text = message.lower()

    # General chat takes priority — these are not operational requests
    if any(kw in text for kw in _GENERAL_CHAT_KEYWORDS):
        return "general_chat"

    # Explicit operational intents
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

    # Anything unrecognized is general chat, not a fault
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
