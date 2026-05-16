import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisSession
from app.repositories import diagnosis as repo
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisResult
from app.services.llm import LLMError, chat_completion
from app.services.vector_search import search_similar


def _build_fallback_diagnosis(query: str, matches: list[dict]) -> DiagnosisResult:
    root_causes: list[str] = []
    steps: list[str] = []
    impact = ""
    runbook_refs: list[dict] = []

    for m in matches[:3]:
        if m["source_type"] == "cases":
            root_causes.append(m["title"])
        if m["source_type"] == "runbooks":
            runbook_refs.append({"id": m["id"], "title": m["title"], "score": m["score"]})

    if not root_causes:
        root_causes.append("基于当前知识库无法自动确定根因，建议逐步排查")

    steps = [
        "1. 收集相关服务的日志和监控数据",
        "2. 对比正常基线，确认异常指标和发生时间点",
        "3. 参考相似案例和 Runbook 中的排查步骤逐项验证",
        "4. 根据验证结果制定修复方案并灰度执行",
    ]

    impact = "故障影响范围需根据实际业务监控进一步确认"

    return DiagnosisResult(
        root_causes=root_causes,
        steps=steps,
        impact=impact,
        runbook_refs=runbook_refs,
    )


def _try_llm_diagnosis(db: Session, query: str, matches: list[dict]) -> DiagnosisResult | None:
    """Try LLM-based diagnosis via llm.py service, return None if unavailable."""
    import json as _json

    context_parts = []
    for m in matches[:3]:
        context_parts.append(f"[{m['source_type']}] {m['title']} (置信度: {m['score']:.0%})")
    context = "\n".join(context_parts) if context_parts else "无相关知识匹配"

    prompt = f"""你是一位资深的云原生运维专家。请根据以下故障描述和知识库参考，生成结构化的诊断报告。

故障描述：
{query}

知识库参考：
{context}

请用 JSON 格式输出诊断结果，包含以下字段：
- root_causes: 可能的根因列表 (至少 1 条)
- steps: 排查步骤列表 (按顺序，每步以数字开头)
- impact: 影响评估 (1-2 句话)
- runbook_refs: 建议参考的 Runbook 列表，每个条目为 {{"id": 整数, "title": "标题", "score": 置信度数值}} (从知识库参考中提取)

只输出 JSON，不要有其他文字。"""

    try:
        content = chat_completion(
            db,
            messages=[
                {"role": "system", "content": "你是一个云原生运维专家，只输出 JSON 格式的诊断结果。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result_dict = _json.loads(content)

        # Normalize runbook_refs: LLM may return strings or dicts
        raw_refs = result_dict.get("runbook_refs", [])
        normalized_refs = []
        runbook_matches = [m for m in matches if m["source_type"] == "runbooks"]
        for ref in raw_refs:
            if isinstance(ref, dict):
                normalized_refs.append(ref)
            elif isinstance(ref, str):
                match = next((m for m in runbook_matches if m["title"] == ref), None)
                if match:
                    normalized_refs.append({"id": match["id"], "title": match["title"], "score": match["score"]})
                else:
                    normalized_refs.append({"id": 0, "title": ref, "score": 0.0})

        return DiagnosisResult(
            root_causes=result_dict.get("root_causes", []),
            steps=result_dict.get("steps", []),
            impact=result_dict.get("impact", ""),
            runbook_refs=normalized_refs,
        )
    except (LLMError, Exception):
        return None


def create_diagnosis(db: Session, payload: DiagnosisCreate) -> DiagnosisSession:
    now = datetime.now()

    # Step 1: Search for similar cases and runbooks
    matches = search_similar(
        db, query=payload.query_text, source_types=["cases", "runbooks"], top_k=5
    )

    # Step 2: Try LLM diagnosis, fall back to rule-based
    llm_result = _try_llm_diagnosis(db, payload.query_text, matches)
    if llm_result is None:
        llm_result = _build_fallback_diagnosis(payload.query_text, matches)

    session = DiagnosisSession(
        query_text=payload.query_text,
        matched_items=json.dumps(matches, ensure_ascii=False),
        llm_response=json.dumps(llm_result.model_dump(), ensure_ascii=False),
        status="completed",
        created_at=now,
        updated_at=now,
    )

    return repo.create(db, session)


def get_diagnosis(db: Session, session_id: int) -> DiagnosisSession | None:
    return repo.get_by_id(db, session_id)


def list_diagnoses(db: Session, offset: int = 0, limit: int = 10) -> tuple[int, list[DiagnosisSession]]:
    return repo.list_recent(db, offset=offset, limit=limit)


def delete_diagnosis(db: Session, session_id: int) -> bool:
    session = repo.get_by_id(db, session_id)
    if not session:
        return False
    repo.delete(db, session)
    return True
