from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


class ModelConfigBase(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50)
    model_type: str = Field(min_length=1, max_length=20)
    endpoint: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=500)
    model_name: str = Field(min_length=1, max_length=100)
    is_active: bool = False
    config_json: str = Field(default="{}", max_length=5000)


class ModelConfigCreate(ModelConfigBase):
    pass


class ModelConfigUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, min_length=1, max_length=50)
    model_type: Optional[str] = Field(default=None, min_length=1, max_length=20)
    endpoint: Optional[str] = Field(default=None, max_length=500)
    api_key: Optional[str] = Field(default=None, max_length=500)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    config_json: Optional[str] = Field(default=None, max_length=5000)


class ModelConfigResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    name: str
    provider: str
    model_type: str
    endpoint: str
    model_name: str
    is_active: bool
    config_json: str
    created_at: datetime
    updated_at: datetime


class ModelConfigListResponse(PaginatedResponse[ModelConfigResponse]):
    pass


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
