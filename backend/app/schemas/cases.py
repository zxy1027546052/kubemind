from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


class CaseBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    symptom: str = Field(default="", max_length=5000)
    root_cause: str = Field(default="", max_length=5000)
    steps: str = Field(default="", max_length=5000)
    impact: str = Field(default="", max_length=5000)
    conclusion: str = Field(default="", max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    severity: str = Field(default="medium", max_length=20)
    status: str = Field(default="open", max_length=20)


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    symptom: Optional[str] = Field(default=None, max_length=5000)
    root_cause: Optional[str] = Field(default=None, max_length=5000)
    steps: Optional[str] = Field(default=None, max_length=5000)
    impact: Optional[str] = Field(default=None, max_length=5000)
    conclusion: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    severity: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, max_length=20)


class CaseResponse(CaseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CasePaginatedResponse(PaginatedResponse[CaseResponse]):
    pass
