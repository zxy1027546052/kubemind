import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import AppException
from app.core.schemas import HealthResponse
from app.seeds.alerts import seed_alerts
from app.seeds.cases import seed_cases
from app.seeds.diagnosis import seed_diagnoses
from app.seeds.knowledge import seed_documents
from app.seeds.model_config import seed_model_configs
from app.seeds.runbooks import seed_runbooks
from app.seeds.workflows import seed_workflows
from app.services import vector_db

logger = logging.getLogger(__name__)


def run_seeds() -> None:
    db = SessionLocal()
    try:
        seed_documents(db)
        seed_cases(db)
        seed_runbooks(db)
        seed_model_configs(db)
        seed_diagnoses(db)
        seed_alerts(db)
        seed_workflows(db)
    finally:
        db.close()


def init_vector_db() -> None:
    db = SessionLocal()
    try:
        vector_db.try_init_on_startup(db)
    except Exception as e:
        logger.warning("Milvus init skipped: %s", e)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_seeds()
    init_vector_db()
    yield


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="AI-powered operations workbench for cloud-native environments.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


app.include_router(api_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse()
