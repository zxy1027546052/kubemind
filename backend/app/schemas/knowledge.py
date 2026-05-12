from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


class DocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=100)
    size: str = Field(default="-", max_length=50)
    content: str = Field(default="", max_length=10000)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    size: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = Field(default=None, max_length=10000)


class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentPaginatedResponse(PaginatedResponse[DocumentResponse]):
    pass
