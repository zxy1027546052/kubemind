import json
import re

from sqlalchemy.orm import Session

# 显式命名空间模式
_NAMESPACE_CN_PATTERN = re.compile(r"([a-z0-9][-a-z0-9]*?)\s*命名空间", re.IGNORECASE)
_NAMESPACE_EN_PATTERN = re.compile(r"namespace\s+['\"]?([a-z0-9][-a-z0-9]*?)['\"]?", re.IGNORECASE)
# 已知的常见命名空间（即使没有显式标注也能识别）
_COMMON_NAMESPACES = {"default", "prod", "dev", "test", "staging", "kube-system", "kube-public", "kube-node-lease"}
# 通用 token 匹配
_NAMESPACE_TOKEN_PATTERN = re.compile(r"\b([a-z][a-z0-9-]{0,253}[a-z0-9])\b", re.IGNORECASE)
_NAMESPACE_BLACKLIST = {"error", "errors", "log", "logs", "show", "view", "check", "query", "pod", "pods", "cpu", "内存", "memory", "help", "你好"}

WORKLOAD_PATTERN = re.compile(
    r"\b([a-z][a-z0-9-]*(?:api|app|demoapp|server|service|worker|gateway|web|frontend|backend)[a-z0-9-]*)\b",
    re.IGNORECASE,
)
IGNORED_WORKLOAD_TOKENS = {
    "error", "errors", "log", "logs", "show", "view", "check", "query",
    "default", "prod", "dev", "test", "staging", "kube-system",
}

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


def classify_intents(message: str, db: Session | None = None) -> list[str]:
    """Detect all applicable intents for a message (supports compound queries)."""
    intents = _classify_all_by_keywords(message)

    if not intents and db is not None:
        llm_intents = _classify_multi_by_llm(message, db)
        if llm_intents:
            return llm_intents

    if not intents:
        single = classify_intent(message, db=db)
        return [single]

    return intents


def _classify_all_by_keywords(message: str) -> list[str]:
    """Scan for ALL matching intents without early return."""
    text = message.lower()
    intents: list[str] = []

    if any(kw in text for kw in _GENERAL_CHAT_KEYWORDS):
        return ["general_chat"]

    if any(kw in text for kw in ("生成排查流程", "创建流程", "create workflow")):
        intents.append("create_workflow")
    if any(kw in text for kw in _FAULT_KEYWORDS):
        intents.append("diagnose_issue")
    if any(kw in text for kw in ("日志", "log", "错误日志")):
        intents.append("query_logs")
    if any(kw in text for kw in ("cpu", "内存", "memory", "指标", "metric")):
        intents.append("query_metric")
    if any(kw in text for kw in ("milvus", "向量库", "向量数据库", "vector", "runbook", "手册", "处理手册", "知识库")):
        intents.append("search_runbook")
    if any(kw in text for kw in ("集群", "节点", "pod")):
        intents.append("query_cluster")

    return list(dict.fromkeys(intents))


def _classify_multi_by_llm(message: str, db: Session) -> list[str]:
    """LLM-based multi-intent classification."""
    try:
        from app.services.llm import chat_completion

        prompt = (
            "你是意图分类器。用户消息可能包含多个意图，请列出所有适用的意图。\n"
            "可选意图: query_metric, query_logs, diagnose_issue, search_runbook, "
            "create_workflow, query_cluster, general_chat\n\n"
            "规则：\n"
            "- 如果用户同时想查指标和日志，返回两个意图\n"
            "- 如果用户描述故障并想看日志，返回 diagnose_issue,query_logs\n"
            "- 用逗号分隔多个意图，不要空格\n"
            "- 只输出意图名称，不要其他文字\n\n"
            f"用户消息：{message}"
        )
        result = chat_completion(
            db,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=64,
        )
        raw = result.strip().lower().replace('"', "").replace("'", "")
        candidates = [i.strip() for i in raw.split(",")]
        valid = [i for i in candidates if i in _VALID_INTENTS]
        return valid if valid else []
    except Exception:
        return []


def extract_entities(message: str, db: Session | None = None, history: list[dict[str, str]] | None = None) -> dict[str, str]:
    entities = _extract_entities_by_regex(message)

    if not entities.get("workload") and db is not None:
        llm_entities = _extract_entities_by_llm(message, db, history)
        entities.update({k: v for k, v in llm_entities.items() if v})

    return entities


def _extract_entities_by_regex(message: str) -> dict[str, str]:
    entities: dict[str, str] = {}

    # 1. 显式命名空间模式: "xxx命名空间" 或 "namespace xxx"
    cn_match = _NAMESPACE_CN_PATTERN.search(message)
    en_match = _NAMESPACE_EN_PATTERN.search(message)
    namespace_raw = None
    if cn_match:
        namespace_raw = cn_match.group(1)
    elif en_match:
        namespace_raw = en_match.group(1)

    # 2. 已知常见命名空间名称（向后兼容，无需显式标注）
    if namespace_raw is None:
        for ns in _COMMON_NAMESPACES:
            if re.search(rf"\b{re.escape(ns)}\b", message, re.IGNORECASE):
                namespace_raw = ns
                break

    # 3. 宽松匹配: 在 Pod/集群上下文中提取未被黑名单拦截的 token
    if namespace_raw is None and any(
        kw in message.lower() for kw in ("命名空间", "namespace", "pod", "pods", "集群", "cluster", "节点", "node")
    ):
        for token in _NAMESPACE_TOKEN_PATTERN.findall(message):
            if token.lower() not in _NAMESPACE_BLACKLIST and token.lower() not in _COMMON_NAMESPACES:
                namespace_raw = token
                break

    # 4. 提取 workload
    workload_match = WORKLOAD_PATTERN.search(message)
    if workload_match and workload_match.group(1).lower() not in IGNORED_WORKLOAD_TOKENS:
        entities["workload"] = workload_match.group(1)
        # 如果仍未提取命名空间，尝试 workload 前的词作为命名空间
        if namespace_raw is None:
            before = message[:workload_match.start()].strip().split()
            if before:
                candidate = before[-1].rstrip("的").rstrip("了")
                if (
                    candidate.lower() not in _NAMESPACE_BLACKLIST
                    and re.match(r"^[a-z][-a-z0-9]*$", candidate, re.IGNORECASE)
                ):
                    namespace_raw = candidate

    if namespace_raw and namespace_raw.lower() not in _NAMESPACE_BLACKLIST:
        entities["namespace"] = namespace_raw.lower()
    if "cpu" in message.lower():
        entities["metric"] = "cpu"
    if "内存" in message or "memory" in message.lower():
        entities["metric"] = "memory"
    return entities


def _extract_entities_by_llm(
    message: str, db: Session, history: list[dict[str, str]] | None = None
) -> dict[str, str]:
    try:
        from app.services.llm import chat_completion

        history_text = ""
        if history:
            recent = history[-4:]
            history_text = "\n".join(
                f"{m['role']}: {m['content']}" for m in recent
            )

        prompt = (
            "从用户消息中提取 Kubernetes 运维相关实体。如果消息中有指代词（它、这个服务等），"
            "请根据对话历史推断实际指代的对象。\n\n"
        )
        if history_text:
            prompt += f"对话历史:\n{history_text}\n\n"
        prompt += (
            f"当前消息: {message}\n\n"
            "请以 JSON 格式返回，只包含能确定的字段:\n"
            '{"workload": "服务/Pod名称", "namespace": "命名空间", "metric": "cpu或memory"}\n'
            "如果无法确定某个字段，该字段值设为空字符串。只输出 JSON，不要其他文字。"
        )
        result = chat_completion(
            db,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=128,
        )
        parsed = json.loads(result.strip().strip("`").removeprefix("json").strip())
        return {k: v for k, v in parsed.items() if isinstance(v, str) and k in ("workload", "namespace", "metric")}
    except Exception:
        return {}
