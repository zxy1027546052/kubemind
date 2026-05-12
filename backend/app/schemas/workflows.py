from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


class WorkflowBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="", max_length=100)
    steps: str = Field(default="[]")
    status: str = Field(default="draft")


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[str] = Field(default=None, max_length=100)
    steps: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)


class WorkflowResponse(WorkflowBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowPaginatedResponse(PaginatedResponse[WorkflowResponse]):
    pass
