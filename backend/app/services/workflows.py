from datetime import datetime

from sqlalchemy.orm import Session

from app.models.workflows import Workflow
from app.repositories import workflows as repo
from app.schemas.workflows import WorkflowCreate, WorkflowUpdate


def list_workflows(
    db: Session,
    query: str = "",
    category: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Workflow]]:
    return repo.list_with_filters(
        db, query=query, category=category, status=status, offset=offset, limit=limit
    )


def get_workflow(db: Session, workflow_id: int) -> Workflow | None:
    return repo.get_by_id(db, workflow_id)


def create_workflow(db: Session, payload: WorkflowCreate) -> Workflow:
    now = datetime.now()
    workflow = Workflow(**payload.model_dump(), created_at=now, updated_at=now)
    return repo.create(db, workflow)


def update_workflow(db: Session, workflow_id: int, payload: WorkflowUpdate) -> Workflow | None:
    workflow = repo.get_by_id(db, workflow_id)
    if not workflow:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workflow, key, value)
    workflow.updated_at = datetime.now()
    return repo.update(db, workflow)


def replace_workflow(db: Session, workflow_id: int, payload: WorkflowCreate) -> Workflow | None:
    workflow = repo.get_by_id(db, workflow_id)
    if not workflow:
        return None
    for key, value in payload.model_dump().items():
        setattr(workflow, key, value)
    workflow.updated_at = datetime.now()
    return repo.update(db, workflow)


def delete_workflow(db: Session, workflow_id: int) -> bool:
    workflow = repo.get_by_id(db, workflow_id)
    if not workflow:
        return False
    repo.delete(db, workflow)
    return True
