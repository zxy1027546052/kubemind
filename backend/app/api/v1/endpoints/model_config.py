from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.schemas import PaginationMeta
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigListResponse,
    ModelConfigResponse,
    ModelConfigUpdate,
    TestConnectionResponse,
)
from app.services.model_config import (
    create_model_config,
    delete_model_config,
    get_model_config,
    list_model_configs,
    test_model_connection,
    update_model_config,
)

router = APIRouter()


@router.get("", response_model=ModelConfigListResponse)
def get_models(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ModelConfigListResponse:
    total, items = list_model_configs(db, offset=offset, limit=limit)
    return ModelConfigListResponse(
        pagination=PaginationMeta(total=total, offset=offset, limit=limit),
        items=[ModelConfigResponse.model_validate(item) for item in items],
    )


@router.post("", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
def post_model(payload: ModelConfigCreate, db: Session = Depends(get_db)) -> ModelConfigResponse:
    return ModelConfigResponse.model_validate(create_model_config(db, payload))


@router.get("/{config_id}", response_model=ModelConfigResponse)
def get_one_model(config_id: int, db: Session = Depends(get_db)) -> ModelConfigResponse:
    config = get_model_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    return ModelConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=ModelConfigResponse)
def put_model(config_id: int, payload: ModelConfigCreate, db: Session = Depends(get_db)) -> ModelConfigResponse:
    config = update_model_config(db, config_id, payload)
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    return ModelConfigResponse.model_validate(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_model(config_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_model_config(db, config_id):
        raise HTTPException(status_code=404, detail="Model config not found")


@router.post("/{config_id}/test", response_model=TestConnectionResponse)
def test_model(config_id: int, db: Session = Depends(get_db)) -> TestConnectionResponse:
    success, message = test_model_connection(db, config_id)
    return TestConnectionResponse(success=success, message=message)
