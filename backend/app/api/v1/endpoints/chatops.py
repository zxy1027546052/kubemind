from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.chatops import ChatOpsMessageRequest, ChatOpsMessageResponse
from app.services.chatops import handle_chatops_message

router = APIRouter()


@router.post("/messages", response_model=ChatOpsMessageResponse)
def post_message(payload: ChatOpsMessageRequest, db: Session = Depends(get_db)) -> ChatOpsMessageResponse:
    return handle_chatops_message(payload, db=db)
