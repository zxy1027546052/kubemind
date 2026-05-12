from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


class AlertBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    severity: str = Field(default="medium")
    source: str = Field(default="manual", max_length=100)
    status: str = Field(default="active")
    assigned_to: str = Field(default="", max_length=100)
    category: str = Field(default="", max_length=100)


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    severity: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None)
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)


class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertPaginatedResponse(PaginatedResponse[AlertResponse]):
    pass
