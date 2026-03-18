from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ResearchJob

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = None
    if job.result:
        try:
            result = json.loads(job.result)
        except Exception:
            result = job.result
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "target": job.target,
        "result": result,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.get("")
def list_jobs(limit: int = 20, db: Session = Depends(get_db)):
    jobs = db.query(ResearchJob).order_by(ResearchJob.created_at.desc()).limit(limit).all()
    return [
        {
            "id": j.id,
            "job_type": j.job_type,
            "status": j.status,
            "target": j.target,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        }
        for j in jobs
    ]
