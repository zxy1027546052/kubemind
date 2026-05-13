from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.schemas.observability import (
    LokiQueryResponse,
    MetricRangeQuery,
    ObservabilityHealth,
    PrometheusQueryResponse,
)
from app.services.observability import get_observability_client

router = APIRouter()


@router.get("/health", response_model=ObservabilityHealth)
def health() -> ObservabilityHealth:
    client = get_observability_client()
    return client.health()


@router.get("/prometheus/query", response_model=PrometheusQueryResponse)
def query_prometheus(q: str = Query(min_length=1)) -> PrometheusQueryResponse:
    client = get_observability_client()
    try:
        result = client.query_prometheus(q)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PrometheusQueryResponse(query=result.query, result_type=result.result_type, points=result.points)


@router.post("/prometheus/query-range", response_model=PrometheusQueryResponse)
def query_prometheus_range(payload: MetricRangeQuery) -> PrometheusQueryResponse:
    client = get_observability_client()
    _validate_time_range(payload.start, payload.end)
    try:
        result = client.query_prometheus_range(
            query=payload.query,
            start=payload.start,
            end=payload.end,
            step=payload.step,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PrometheusQueryResponse(query=result.query, result_type=result.result_type, points=result.points)


@router.get("/loki/query-range", response_model=LokiQueryResponse)
def query_loki_range(
    q: str = Query(min_length=1),
    start: datetime = Query(),
    end: datetime = Query(),
    limit: int = Query(default=100, ge=1, le=200),
) -> LokiQueryResponse:
    client = get_observability_client()
    _validate_time_range(start, end)
    try:
        result = client.query_loki_range(query=q, start=start, end=end, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return LokiQueryResponse(query=result.query, entries=result.entries)


def _validate_time_range(start: datetime, end: datetime) -> None:
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be greater than start")
