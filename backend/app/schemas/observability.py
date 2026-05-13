from datetime import datetime

from pydantic import BaseModel, Field


class DataSourceHealth(BaseModel):
    enabled: bool
    status: str
    message: str


class ObservabilityHealth(BaseModel):
    prometheus: DataSourceHealth
    loki: DataSourceHealth


class PrometheusPoint(BaseModel):
    metric: dict[str, str]
    timestamp: datetime
    value: float


class PrometheusQueryResponse(BaseModel):
    query: str
    result_type: str
    points: list[PrometheusPoint]


class LokiLogEntry(BaseModel):
    labels: dict[str, str]
    timestamp: datetime
    line: str


class LokiQueryResponse(BaseModel):
    query: str
    entries: list[LokiLogEntry]


class MetricRangeQuery(BaseModel):
    query: str = Field(min_length=1)
    start: datetime
    end: datetime
    step: str = Field(default="60s", min_length=1)


class LogQuery(BaseModel):
    query: str = Field(min_length=1)
    start: datetime
    end: datetime
    limit: int = Field(default=100, ge=1, le=200)
