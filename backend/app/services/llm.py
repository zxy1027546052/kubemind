"""LLM chat completion service — OpenAI-compatible (DeepSeek, OpenAI, etc.)."""

import json
import urllib.request
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig


class LLMError(Exception):
    pass


def get_active_llm_config(db: Session) -> ModelConfig | None:
    return (
        db.query(ModelConfig)
        .filter(ModelConfig.model_type == "llm", ModelConfig.is_active.is_(True))
        .first()
    )


def chat_completion(
    db: Session,
    messages: list[dict],
    config: ModelConfig | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    if config is None:
        config = get_active_llm_config(db)
    if not config:
        raise LLMError("No active LLM config found")
    if not config.api_key:
        raise LLMError("LLM config has no API key")

    payload = json.dumps({
        "model": config.model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{config.endpoint.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def chat_completion_stream(
    db: Session,
    messages: list[dict],
    config: ModelConfig | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Generator[str, None, None]:
    """Stream chat completion tokens via SSE from an OpenAI-compatible endpoint."""
    if config is None:
        config = get_active_llm_config(db)
    if not config:
        raise LLMError("No active LLM config found")
    if not config.api_key:
        raise LLMError("LLM config has no API key")

    payload = json.dumps({
        "model": config.model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{config.endpoint.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line or line.startswith(":"):
                continue
            if line == "data: [DONE]":
                break
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
