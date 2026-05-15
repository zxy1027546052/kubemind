from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.runtime import event_bus_registry
from app.schemas.chatops import ChatOpsMessageRequest, ChatOpsMessageResponse
from app.services.chatops import handle_chatops_message, handle_chatops_message_stream

router = APIRouter()


@router.post("/messages", response_model=ChatOpsMessageResponse)
def post_message(payload: ChatOpsMessageRequest, db: Session = Depends(get_db)) -> ChatOpsMessageResponse:
    return handle_chatops_message(payload, db=db)


@router.post("/messages/stream")
def post_message_stream(payload: ChatOpsMessageRequest, db: Session = Depends(get_db)):
    return StreamingResponse(
        handle_chatops_message_stream(payload, db=db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions/{session_id}/trace")
def get_session_trace(session_id: str):
    """Retrieve the runtime event history for a session (if still in memory)."""
    bus = event_bus_registry.get_or_create(session_id)
    events = [
        {"type": e.type, "timestamp": e.timestamp, "data": e.data}
        for e in bus.events
    ]
    return {"session_id": session_id, "event_count": len(events), "events": events}
