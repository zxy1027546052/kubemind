from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.schemas import PaginationMeta
from app.schemas.cases import (
    CaseCreate,
    CasePaginatedResponse,
    CaseResponse,
    CaseUpdate,
)
from app.services.cases import (
    create_case,
    delete_case,
    get_case,
    list_cases,
    replace_case,
    update_case,
)

router = APIRouter()


@router.get("", response_model=CasePaginatedResponse)
def get_cases(
    query: str = Query(default=""),
    category: str = Query(default=""),
    severity: str = Query(default=""),
    status: str = Query(default=""),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CasePaginatedResponse:
    total, items = list_cases(
        db, query=query, category=category, severity=severity, status=status, offset=offset, limit=limit
    )
    return CasePaginatedResponse(
        pagination=PaginationMeta(total=total, offset=offset, limit=limit),
        items=[CaseResponse.model_validate(item) for item in items],
    )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def post_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseResponse:
    return CaseResponse.model_validate(create_case(db, payload))


@router.get("/{case_id}", response_model=CaseResponse)
def get_one_case(case_id: int, db: Session = Depends(get_db)) -> CaseResponse:
    case = get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse.model_validate(case)


@router.put("/{case_id}", response_model=CaseResponse)
def put_case(case_id: int, payload: CaseCreate, db: Session = Depends(get_db)) -> CaseResponse:
    case = replace_case(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse.model_validate(case)


@router.patch("/{case_id}", response_model=CaseResponse)
def patch_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)) -> CaseResponse:
    case = update_case(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse.model_validate(case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_case(case_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_case(db, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
