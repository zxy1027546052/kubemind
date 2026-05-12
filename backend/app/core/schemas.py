from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "kubemind-backend"


class PaginationMeta(BaseModel):
    total: int
    offset: int
    limit: int


class PaginatedResponse(BaseModel, Generic[T]):
    pagination: PaginationMeta
    items: list[T]
