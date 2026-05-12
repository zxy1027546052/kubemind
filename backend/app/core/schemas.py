from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "kubemind-backend"


class DocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=100)
    size: str = Field(default="-", max_length=50)
    content: str = Field(default="", max_length=10000)


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    items: list[Document]
