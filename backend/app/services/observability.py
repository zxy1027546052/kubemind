from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import json

from app.core.config import settings
from app.schemas.observability import DataSourceHealth, ObservabilityHealth


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class PrometheusQueryResult:
    query: str
    result_type: str
    points: list[dict[str, Any]]


@dataclass(frozen=True)
class LokiQueryResult:
    query: str
    entries: list[dict[str, Any]]


class ObservabilityClient:
    def __init__(
        self,
        prometheus_base_url: str | None = None,
        loki_base_url: str | None = None,
        prometheus_timeout_seconds: float | None = None,
        loki_timeout_seconds: float | None = None,
    ) -> None:
        self.prometheus_base_url = (prometheus_base_url if prometheus_base_url is not None else settings.PROMETHEUS_BASE_URL).rstrip("/")
        self.loki_base_url = (loki_base_url if loki_base_url is not None else settings.LOKI_BASE_URL).rstrip("/")
        self.prometheus_timeout_seconds = prometheus_timeout_seconds or settings.PROMETHEUS_TIMEOUT_SECONDS
        self.loki_timeout_seconds = loki_timeout_seconds or settings.LOKI_TIMEOUT_SECONDS

    def health(self) -> ObservabilityHealth:
        return ObservabilityHealth(
            prometheus=self._source_health(self.prometheus_base_url, "PROMETHEUS_BASE_URL"),
            loki=self._source_health(self.loki_base_url, "LOKI_BASE_URL"),
        )

    def query_prometheus(self, query: str) -> PrometheusQueryResult:
        payload = self._get_json(
            base_url=self.prometheus_base_url,
            path="/api/v1/query",
            params={"query": query},
            timeout_seconds=self.prometheus_timeout_seconds,
            source_name="Prometheus",
        )
        result_type = str(payload.get("data", {}).get("resultType", ""))
        return PrometheusQueryResult(query=query, result_type=result_type, points=build_prometheus_points(payload))

    def query_prometheus_range(self, query: str, start: datetime, end: datetime, step: str) -> PrometheusQueryResult:
        payload = self._get_json(
            base_url=self.prometheus_base_url,
            path="/api/v1/query_range",
            params={
                "query": query,
                "start": _to_unix_seconds(start),
                "end": _to_unix_seconds(end),
                "step": step,
            },
            timeout_seconds=self.prometheus_timeout_seconds,
            source_name="Prometheus",
        )
        result_type = str(payload.get("data", {}).get("resultType", ""))
        return PrometheusQueryResult(query=query, result_type=result_type, points=build_prometheus_points(payload))

    def query_loki_range(self, query: str, start: datetime, end: datetime, limit: int) -> LokiQueryResult:
        payload = self._get_json(
            base_url=self.loki_base_url,
            path="/loki/api/v1/query_range",
            params={
                "query": query,
                "start": _to_unix_nanoseconds(start),
                "end": _to_unix_nanoseconds(end),
                "limit": limit,
                "direction": "BACKWARD",
            },
            timeout_seconds=self.loki_timeout_seconds,
            source_name="Loki",
        )
        return LokiQueryResult(query=query, entries=build_loki_entries(payload))

    def _source_health(self, base_url: str, setting_name: str) -> DataSourceHealth:
        if not base_url:
            return DataSourceHealth(
                enabled=False,
                status="disabled",
                message=f"{setting_name} is not configured",
            )
        return DataSourceHealth(enabled=True, status="configured", message=f"{setting_name} is configured")

    def _get_json(
        self,
        base_url: str,
        path: str,
        params: dict[str, Any],
        timeout_seconds: float,
        source_name: str,
    ) -> JsonObject:
        if not base_url:
            raise RuntimeError(f"{source_name} base URL is not configured")

        url = f"{base_url}{path}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(f"{source_name} request failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"{source_name} request failed: {exc.reason}") from exc

        payload = json.loads(body)
        if payload.get("status") not in ("success", None):
            message = payload.get("error") or payload.get("errorType") or "unknown error"
            raise RuntimeError(f"{source_name} returned error: {message}")
        return payload


def get_observability_client() -> ObservabilityClient:
    return ObservabilityClient()


def build_prometheus_points(payload: JsonObject) -> list[dict[str, Any]]:
    results = payload.get("data", {}).get("result", [])
    points: list[dict[str, Any]] = []
    for result in results:
        metric = result.get("metric", {})
        if "values" in result:
            for timestamp, value in result["values"]:
                points.append({
                    "metric": metric,
                    "timestamp": datetime.fromtimestamp(float(timestamp), tz=timezone.utc),
                    "value": float(value),
                })
            continue
        if "value" in result:
            timestamp, value = result["value"]
            points.append({
                "metric": metric,
                "timestamp": datetime.fromtimestamp(float(timestamp), tz=timezone.utc),
                "value": float(value),
            })
    return points


def build_loki_entries(payload: JsonObject) -> list[dict[str, Any]]:
    results = payload.get("data", {}).get("result", [])
    entries: list[dict[str, Any]] = []
    for result in results:
        labels = result.get("stream", {})
        for timestamp_ns, line in result.get("values", []):
            entries.append({
                "labels": labels,
                "timestamp": datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000, tz=timezone.utc),
                "line": line,
            })
    return entries


def _to_unix_seconds(value: datetime) -> int:
    return int(value.timestamp())


def _to_unix_nanoseconds(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)
