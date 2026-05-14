from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
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
