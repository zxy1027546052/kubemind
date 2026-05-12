from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.schemas import HealthResponse
from app.modules.knowledge.router import router as documents_router


app = FastAPI(
    title="KubeMind Backend",
    version="0.1.0",
    description="Knowledge center MVP backend for KubeMind.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse()
