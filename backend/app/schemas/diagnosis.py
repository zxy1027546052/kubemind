from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DiagnosisCreate(BaseModel):
    query_text: str = Field(min_length=1, max_length=5000)


class MatchedItem(BaseModel):
    id: int
    source_type: str
    title: str
    score: float


class DiagnosisResult(BaseModel):
    root_causes: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    impact: str = ""
    runbook_refs: list[dict] = Field(default_factory=list)


class DiagnosisResponse(BaseModel):
    id: int
    query_text: str
    matched_items: list[MatchedItem] = Field(default_factory=list)
    llm_response: DiagnosisResult = Field(default_factory=DiagnosisResult)
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
