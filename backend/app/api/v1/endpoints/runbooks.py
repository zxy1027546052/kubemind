from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.schemas import PaginationMeta
from app.schemas.runbooks import (
    RunbookCreate,
    RunbookPaginatedResponse,
    RunbookResponse,
    RunbookUpdate,
)
from app.services.runbooks import (
    create_runbook,
    delete_runbook,
    get_runbook,
    list_runbooks,
    replace_runbook,
    update_runbook,
)

router = APIRouter()


@router.get("", response_model=RunbookPaginatedResponse)
def get_runbooks(
    query: str = Query(default=""),
    category: str = Query(default=""),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> RunbookPaginatedResponse:
    total, items = list_runbooks(db, query=query, category=category, offset=offset, limit=limit)
    return RunbookPaginatedResponse(
        pagination=PaginationMeta(total=total, offset=offset, limit=limit),
        items=[RunbookResponse.model_validate(item) for item in items],
    )


@router.post("", response_model=RunbookResponse, status_code=status.HTTP_201_CREATED)
def post_runbook(payload: RunbookCreate, db: Session = Depends(get_db)) -> RunbookResponse:
    return RunbookResponse.model_validate(create_runbook(db, payload))


@router.get("/{runbook_id}", response_model=RunbookResponse)
def get_one_runbook(runbook_id: int, db: Session = Depends(get_db)) -> RunbookResponse:
    runbook = get_runbook(db, runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return RunbookResponse.model_validate(runbook)


@router.put("/{runbook_id}", response_model=RunbookResponse)
def put_runbook(runbook_id: int, payload: RunbookCreate, db: Session = Depends(get_db)) -> RunbookResponse:
    runbook = replace_runbook(db, runbook_id, payload)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return RunbookResponse.model_validate(runbook)


@router.patch("/{runbook_id}", response_model=RunbookResponse)
def patch_runbook(runbook_id: int, payload: RunbookUpdate, db: Session = Depends(get_db)) -> RunbookResponse:
    runbook = update_runbook(db, runbook_id, payload)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return RunbookResponse.model_validate(runbook)


@router.delete("/{runbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_runbook(runbook_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_runbook(db, runbook_id):
        raise HTTPException(status_code=404, detail="Runbook not found")
