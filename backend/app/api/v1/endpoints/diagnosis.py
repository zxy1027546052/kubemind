import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisResponse, DiagnosisResult, MatchedItem
from app.services.diagnosis import create_diagnosis, delete_diagnosis, get_diagnosis, list_diagnoses

router = APIRouter()


def _to_response(session) -> DiagnosisResponse:
    matched = json.loads(session.matched_items) if session.matched_items else []
    llm_result_dict = json.loads(session.llm_response) if session.llm_response else {}
    return DiagnosisResponse(
        id=session.id,
        query_text=session.query_text,
        matched_items=[MatchedItem(**m) for m in matched],
        llm_response=DiagnosisResult(**llm_result_dict) if llm_result_dict else DiagnosisResult(),
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("", response_model=list[DiagnosisResponse])
def get_sessions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[DiagnosisResponse]:
    _, items = list_diagnoses(db, offset=offset, limit=limit)
    return [_to_response(item) for item in items]


@router.post("", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def post_diagnosis(payload: DiagnosisCreate, db: Session = Depends(get_db)) -> DiagnosisResponse:
    session = create_diagnosis(db, payload)
    return _to_response(session)


@router.get("/{session_id}", response_model=DiagnosisResponse)
def get_one_diagnosis(session_id: int, db: Session = Depends(get_db)) -> DiagnosisResponse:
    session = get_diagnosis(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Diagnosis session not found")
    return _to_response(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_diagnosis(session_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_diagnosis(db, session_id):
        raise HTTPException(status_code=404, detail="Diagnosis session not found")
