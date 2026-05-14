"""LLM chat completion service — powered by LangChain (OpenAI-compatible)."""

from collections.abc import Generator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
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


def _resolve_config(db: Session, config: ModelConfig | None) -> ModelConfig:
    if config is None:
        config = get_active_llm_config(db)
    if not config:
        raise LLMError("No active LLM config found")
    if not config.api_key:
        raise LLMError("LLM config has no API key")
    return config


def _build_chat_model(config: ModelConfig, temperature: float, max_tokens: int) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.model_name,
        api_key=config.api_key,
        base_url=f"{config.endpoint.rstrip('/')}",
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=60,
        max_retries=2,
    )


def _to_langchain_messages(messages: list[dict]) -> list[BaseMessage]:
    result: list[BaseMessage] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            result.append(SystemMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        else:
            result.append(HumanMessage(content=content))
    return result


def chat_completion(
    db: Session,
    messages: list[dict],
    config: ModelConfig | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    config = _resolve_config(db, config)
    model = _build_chat_model(config, temperature, max_tokens)
    result = model.invoke(_to_langchain_messages(messages))
    return result.content


def chat_completion_stream(
    db: Session,
    messages: list[dict],
    config: ModelConfig | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Generator[str, None, None]:
    """Stream chat completion tokens via LangChain's streaming interface."""
    config = _resolve_config(db, config)
    model = _build_chat_model(config, temperature, max_tokens)
    for chunk in model.stream(_to_langchain_messages(messages)):
        if chunk.content:
            yield chunk.content
