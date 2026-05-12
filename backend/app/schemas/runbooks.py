from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


class RunbookBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    scenario: str = Field(default="", max_length=5000)
    steps: str = Field(default="", max_length=5000)
    risk: str = Field(default="", max_length=5000)
    rollback: str = Field(default="", max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    tags: str = Field(default="", max_length=200)


class RunbookCreate(RunbookBase):
    pass


class RunbookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    scenario: Optional[str] = Field(default=None, max_length=5000)
    steps: Optional[str] = Field(default=None, max_length=5000)
    risk: Optional[str] = Field(default=None, max_length=5000)
    rollback: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tags: Optional[str] = Field(default=None, max_length=200)


class RunbookResponse(RunbookBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunbookPaginatedResponse(PaginatedResponse[RunbookResponse]):
    pass
