from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.schemas import PaginationMeta
from app.schemas.workflows import (
    WorkflowCreate,
    WorkflowPaginatedResponse,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services.workflows import (
    create_workflow,
    delete_workflow,
    get_workflow,
    list_workflows,
    replace_workflow,
    update_workflow,
)

router = APIRouter()


@router.get("", response_model=WorkflowPaginatedResponse)
def get_workflows(
    query: str = Query(default=""),
    category: str = Query(default=""),
    status: str = Query(default=""),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> WorkflowPaginatedResponse:
    total, items = list_workflows(
        db, query=query, category=category, status=status, offset=offset, limit=limit
    )
    return WorkflowPaginatedResponse(
        pagination=PaginationMeta(total=total, offset=offset, limit=limit),
        items=[WorkflowResponse.model_validate(item) for item in items],
    )


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def post_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> WorkflowResponse:
    return WorkflowResponse.model_validate(create_workflow(db, payload))


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_one_workflow(workflow_id: int, db: Session = Depends(get_db)) -> WorkflowResponse:
    workflow = get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def put_workflow(workflow_id: int, payload: WorkflowCreate, db: Session = Depends(get_db)) -> WorkflowResponse:
    workflow = replace_workflow(db, workflow_id, payload)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse.model_validate(workflow)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def patch_workflow(workflow_id: int, payload: WorkflowUpdate, db: Session = Depends(get_db)) -> WorkflowResponse:
    workflow = update_workflow(db, workflow_id, payload)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_workflow(workflow_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_workflow(db, workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
