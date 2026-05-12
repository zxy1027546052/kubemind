from fastapi import APIRouter

from app.api.v1.endpoints import cases, knowledge, model_config, runbooks

api_router = APIRouter(prefix="/api")

api_router.include_router(knowledge.router, prefix="/documents", tags=["documents"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(runbooks.router, prefix="/runbooks", tags=["runbooks"])
api_router.include_router(model_config.router, prefix="/models", tags=["models"])
