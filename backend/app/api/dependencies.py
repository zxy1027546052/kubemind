from app.core.database import get_db


def pagination_params(offset: int = 0, limit: int = 20) -> dict:
    return {"offset": max(0, offset), "limit": min(100, max(1, limit))}
