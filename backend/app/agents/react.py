"""ReAct (Reasoning + Acting) executor for the KubeMind ops agent.

Implements a Think → Act → Observe loop where the LLM autonomously decides
which tools to call and when it has enough evidence to produce a final answer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session

from app.agents.nodes import _structure_tool_result
from app.agents.state import OpsGraphState
from app.services.llm import chat_completion, chat_completion_stream
from app.services.mcp import MCPService
from app.services.ops_tools import build_ops_tool_registry, ToolSpec
from app.services.vector_search import search_similar

MAX_ITERATIONS = 5

_TOOL_REGISTRY: dict[str, ToolSpec] | None = None


def _get_tool_registry() -> dict[str, ToolSpec]:
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is None:
        _TOOL_REGISTRY = build_ops_tool_registry()
    return _TOOL_REGISTRY


def _build_tool_descriptions() -> str:
    lines = []
    for spec in _get_tool_registry().values():
        params_str = json.dumps(spec.parameters, ensure_ascii=False)
        lines.append(f"- {spec.name}: {spec.description}\n  参数: {params_str}")
    lines.append("- vector_search: 在知识库中进行向量相似度搜索\n  参数: {\"query\": \"string\"}")
    return "\n".join(lines)


REACT_SYSTEM_PROMPT = """你是 KubeMind 智能运维专家。你可以通过调用工具来收集证据，然后给出诊断分析。

## 可用工具
{tool_descriptions}

## 输出格式
每一步，你必须严格输出以下 JSON 格式之一：

调用工具时：
{{"thought": "你的思考过程", "action": "工具名称", "action_input": {{"参数名": "参数值"}}}}

当你收集了足够的证据，准备给出最终回答时：
{{"thought": "总结分析", "action": "finish", "answer": "你的最终诊断和建议"}}

## 规则
- 每次只调用一个工具
- 根据观察结果决定下一步行动
- 最多调用 {max_iterations} 次工具后必须给出最终回答
- 最终回答用中文，包含：问题分析、可能原因、建议操作
- 只输出 JSON，不要输出其他内容
"""

# PLACEHOLDER_REACT_CONTINUE


class ReactExecutor:
    def __init__(self, db: Session, state: OpsGraphState, mcp_service: MCPService | None = None):
        self.db = db
        self.state = state
        self.mcp_service = mcp_service or MCPService()
        self.scratchpad: list[dict[str, Any]] = []

    def run(self) -> OpsGraphState:
        messages = self._build_initial_messages()

        for i in range(MAX_ITERATIONS):
            response = chat_completion(self.db, messages, temperature=0.1, max_tokens=1024)
            parsed = self._parse_action(response)

            if parsed["action"] == "finish":
                self.state["llm_reply"] = parsed.get("answer", "")
                self._append_trace(f"ReAct finish after {i + 1} iterations")
                break

            observation = self._execute_tool(parsed["action"], parsed.get("action_input", {}))
            self.scratchpad.append({
                "thought": parsed.get("thought", ""),
                "action": parsed["action"],
                "action_input": parsed.get("action_input", {}),
                "observation": observation[:2000],
            })
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Observation:\n{observation[:3000]}"})
            self._append_trace(f"ReAct step {i + 1}: {parsed['action']}")
        else:
            self._force_finish(messages)

        return self.state

    def run_stream(self) -> Generator[str, None, None]:
        messages = self._build_initial_messages()

        for i in range(MAX_ITERATIONS):
            response = chat_completion(self.db, messages, temperature=0.1, max_tokens=1024)
            parsed = self._parse_action(response)

            yield _sse("react.thought", {"step": i + 1, "thought": parsed.get("thought", "")})

            if parsed["action"] == "finish":
                self.state["llm_reply"] = parsed.get("answer", "")
                self._append_trace(f"ReAct finish after {i + 1} iterations")
                break

            yield _sse("react.action", {
                "step": i + 1,
                "tool": parsed["action"],
                "params": parsed.get("action_input", {}),
            })

            observation = self._execute_tool(parsed["action"], parsed.get("action_input", {}))

            yield _sse("react.observation", {
                "step": i + 1,
                "tool": parsed["action"],
                "result_preview": observation[:500],
            })

            self.scratchpad.append({
                "thought": parsed.get("thought", ""),
                "action": parsed["action"],
                "action_input": parsed.get("action_input", {}),
                "observation": observation[:2000],
            })
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Observation:\n{observation[:3000]}"})
            self._append_trace(f"ReAct step {i + 1}: {parsed['action']}")
        else:
            self._force_finish(messages)

    # PLACEHOLDER_REACT_METHODS

    def _build_initial_messages(self) -> list[dict[str, str]]:
        tool_descriptions = _build_tool_descriptions()
        system_prompt = REACT_SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            max_iterations=MAX_ITERATIONS,
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for msg in self.state.get("conversation_history", [])[-6:]:
            messages.append(msg)

        intents = self.state.get("intents", []) or [self.state["intent"]]
        entities = self.state["entities"]
        user_context = (
            f"用户问题: {self.state['user_query']}\n"
            f"检测到的意图: {', '.join(intents)}\n"
            f"已提取实体: {json.dumps(entities, ensure_ascii=False)}\n\n"
            "请开始分析，调用合适的工具收集证据。"
        )
        messages.append({"role": "user", "content": user_context})
        return messages

    def _execute_tool(self, tool_name: str, params: dict) -> str:
        if tool_name == "vector_search":
            return self._execute_vector_search(params)

        result = self.mcp_service.execute_tool(
            db=self.db,
            tool_name=tool_name,
            params=params,
            session_id=self.state["session_id"],
            namespace=params.get("namespace", ""),
        )

        status = "executed" if result.get("success") else "error"
        self.state["tool_calls"].append({
            "tool": tool_name,
            "status": status,
            "namespace": params.get("namespace", ""),
            "workload": self.state["entities"].get("workload", ""),
            "duration_ms": result.get("duration_ms", 0),
        })

        structured = _structure_tool_result(result, tool_name)
        self.state["evidence"].append({
            "source": "mcp",
            "title": f"{tool_name} {status}",
            "summary": structured,
            "score": 1.0 if result.get("success") else 0.0,
        })
        return structured

    def _execute_vector_search(self, params: dict) -> str:
        query = params.get("query", self.state["user_query"])
        results = search_similar(
            self.db,
            query=query,
            source_types=["documents", "cases", "runbooks"],
            top_k=5,
        )
        if not results:
            self.state["evidence"].append({
                "source": "milvus",
                "title": "向量搜索无结果",
                "summary": f"未找到与 '{query}' 相关的知识",
                "score": 0.0,
            })
            return "向量搜索未找到匹配内容。"

        lines = []
        for item in results:
            self.state["evidence"].append({
                "source": "milvus",
                "title": item.get("title", ""),
                "summary": f"{item.get('source_type', '')}#{item.get('id', 0)} score={item.get('score', 0)}",
                "score": item.get("score", 0),
                "source_type": item.get("source_type", ""),
                "source_id": item.get("id", 0),
            })
            lines.append(f"[{item.get('source_type', '')}] {item.get('title', '')} (score={item.get('score', 0):.2f})")
        return f"找到 {len(results)} 条相关知识:\n" + "\n".join(lines)

    def _force_finish(self, messages: list[dict[str, str]]) -> None:
        messages.append({"role": "user", "content": "你已达到最大工具调用次数。请立即根据已收集的证据给出最终回答。输出: {\"thought\": \"...\", \"action\": \"finish\", \"answer\": \"...\"}"})
        response = chat_completion(self.db, messages, temperature=0.3, max_tokens=1024)
        parsed = self._parse_action(response)
        self.state["llm_reply"] = parsed.get("answer", response)
        self._append_trace("ReAct forced finish at max iterations")

    def _parse_action(self, response: str) -> dict[str, Any]:
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"^```(?:json)?\s*", "", response)
            response = re.sub(r"\s*```$", "", response)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\{[^{}]*\"action\"[^{}]*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {"thought": response, "action": "finish", "answer": response}

    def _append_trace(self, message: str) -> None:
        self.state["trace"].append({"agent": "ReactExecutor", "message": message})


def _sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
