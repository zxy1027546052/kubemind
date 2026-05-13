from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    anomalies,
    cases,
    chatops,
    clusters,
    diagnosis,
    knowledge,
    model_config,
    observability,
    runbooks,
    search,
    workflows,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(knowledge.router, prefix="/documents", tags=["documents"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(runbooks.router, prefix="/runbooks", tags=["runbooks"])
api_router.include_router(model_config.router, prefix="/models", tags=["models"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(chatops.router, prefix="/chatops", tags=["chatops"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(clusters.router, prefix="/clusters", tags=["clusters"])
api_router.include_router(observability.router, prefix="/observability", tags=["observability"])
