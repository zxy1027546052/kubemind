from datetime import datetime

from pydantic import BaseModel, Field


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class AnomalyDetectRequest(BaseModel):
    metric_name: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    resource_name: str = Field(min_length=1)
    namespace: str = Field(default="")
    window: str = Field(default="15m", min_length=1)
    points: list[MetricPoint] = Field(min_length=2)


class AnomalyEvent(BaseModel):
    metric_name: str
    resource_type: str
    resource_name: str
    namespace: str
    window: str
    value: float
    baseline: float
    upper_bound: float
    lower_bound: float
    score: float
    severity: str
    evidence: list[str]
    detected_at: datetime


class AnomalyDetectResponse(BaseModel):
    total: int
    items: list[AnomalyEvent]
    alert_ids: list[int] = Field(default_factory=list)
