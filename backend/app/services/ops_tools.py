from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from app.services.k8s import K8sClient, get_k8s_client
from app.services.observability import ObservabilityClient, get_observability_client


JsonObject = dict[str, Any]
ToolHandler = Callable[..., JsonObject]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: str
    risk_level: str
    description: str
    parameters: JsonObject
    handler: ToolHandler
    timeout_ms: int = 30000
    retry: int = 0
    is_read_only: bool = True


def build_ops_tool_registry(
    k8s_client_factory: Callable[[], K8sClient] = get_k8s_client,
    observability_client_factory: Callable[[], ObservabilityClient] = get_observability_client,
) -> dict[str, ToolSpec]:
    return {
        "k8s_get_pods": ToolSpec(
            name="k8s_get_pods",
            category="kubernetes",
            risk_level="low",
            timeout_ms=15000,
            retry=1,
            description="List Kubernetes pods across all namespaces or one namespace.",
            parameters={"namespace": "string optional"},
            handler=lambda namespace="": {"items": k8s_client_factory().get_pods(namespace=namespace or "")},
        ),
        "k8s_get_events": ToolSpec(
            name="k8s_get_events",
            category="kubernetes",
            risk_level="low",
            timeout_ms=15000,
            retry=1,
            description="List Kubernetes events, optionally filtered by namespace and involved object.",
            parameters={"namespace": "string optional", "involved_object_name": "string optional", "limit": "integer optional"},
            handler=lambda namespace="", involved_object_name="", limit=50: {
                "items": k8s_client_factory().get_events(
                    namespace=namespace or "",
                    involved_object_name=involved_object_name or "",
                    limit=int(limit),
                )
            },
        ),
        "k8s_get_pod_logs": ToolSpec(
            name="k8s_get_pod_logs",
            category="kubernetes",
            risk_level="medium",
            timeout_ms=15000,
            retry=1,
            description="Read recent logs from one Kubernetes pod.",
            parameters={"name": "string", "namespace": "string optional", "tail_lines": "integer optional"},
            handler=lambda name, namespace="default", tail_lines=100: k8s_client_factory().get_pod_logs(
                name=name,
                namespace=namespace or "default",
                tail_lines=int(tail_lines),
            ),
        ),
        "k8s_describe_pod": ToolSpec(
            name="k8s_describe_pod",
            category="kubernetes",
            risk_level="medium",
            timeout_ms=15000,
            retry=1,
            description="Describe one Kubernetes pod including status, containers, conditions, and recent metadata.",
            parameters={"name": "string", "namespace": "string optional"},
            handler=lambda name, namespace="default": k8s_client_factory().describe_pod(name=name, namespace=namespace or "default"),
        ),
        "prometheus_query": ToolSpec(
            name="prometheus_query",
            category="observability",
            risk_level="low",
            description="Run a Prometheus instant query.",
            parameters={"query": "string"},
            handler=lambda query: _prometheus_result_to_dict(observability_client_factory().query_prometheus(query=query)),
        ),
        "prometheus_range_query": ToolSpec(
            name="prometheus_range_query",
            category="observability",
            risk_level="low",
            description="Run a Prometheus range query.",
            parameters={"query": "string", "start": "datetime", "end": "datetime", "step": "string"},
            handler=lambda query, start, end, step="30s": _prometheus_result_to_dict(
                observability_client_factory().query_prometheus_range(
                    query=query,
                    start=_parse_datetime(start),
                    end=_parse_datetime(end),
                    step=step,
                )
            ),
        ),
        "loki_query": ToolSpec(
            name="loki_query",
            category="observability",
            risk_level="low",
            description="Run a Loki range log query.",
            parameters={"query": "string", "start": "datetime", "end": "datetime", "limit": "integer optional"},
            handler=lambda query, start, end, limit=100: _loki_result_to_dict(
                observability_client_factory().query_loki_range(
                    query=query,
                    start=_parse_datetime(start),
                    end=_parse_datetime(end),
                    limit=int(limit),
                )
            ),
        ),
    }


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _prometheus_result_to_dict(result: Any) -> JsonObject:
    return {
        "query": result.query,
        "result_type": result.result_type,
        "points": _serialize_value(result.points),
    }


def _loki_result_to_dict(result: Any) -> JsonObject:
    return {
        "query": result.query,
        "entries": _serialize_value(result.entries),
    }
