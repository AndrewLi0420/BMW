from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ConferenceProceeding

router = APIRouter(prefix="/api/proceedings", tags=["proceedings"])


def _proc_dict(p: ConferenceProceeding) -> dict:
    return {
        "id": p.id,
        "company_id": p.company_id,
        "company_name": p.company_name,
        "title": p.title,
        "event_name": p.event_name,
        "event_date": p.event_date,
        "location": p.location,
        "authors": json.loads(p.authors or "[]"),
        "technologies": json.loads(p.technologies or "[]"),
        "partners_mentioned": json.loads(p.partners_mentioned or "[]"),
        "results_summary": p.results_summary,
        "source_type": p.source_type,
        "source_url": p.source_url,
        "file_path": p.file_path,
        "topics": json.loads(p.topics or "[]"),
        "created_at": p.created_at,
    }


@router.get("")
def list_proceedings(
    company_id: int | None = None,
    technology: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ConferenceProceeding)
    if company_id:
        q = q.filter(ConferenceProceeding.company_id == company_id)
    if technology:
        q = q.filter(ConferenceProceeding.technologies.like(f"%{technology}%"))
    if search:
        q = q.filter(
            ConferenceProceeding.title.ilike(f"%{search}%")
            | ConferenceProceeding.results_summary.ilike(f"%{search}%")
            | ConferenceProceeding.company_name.ilike(f"%{search}%")
        )
    return [_proc_dict(p) for p in q.order_by(ConferenceProceeding.event_date.desc()).all()]
