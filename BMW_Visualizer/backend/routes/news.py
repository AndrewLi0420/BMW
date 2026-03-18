from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import NewsHeadline, ResearchJob

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/news", tags=["news"])


def _news_dict(n: NewsHeadline) -> dict:
    return {
        "id": n.id,
        "company_id": n.company_id,
        "company_name": n.company_name,
        "news_headline": n.news_headline,
        "category": n.category,
        "partners": json.loads(n.partners or "[]"),
        "news_source": n.news_source,
        "date_of_article": n.date_of_article,
        "location": n.location,
        "topics": json.loads(n.topics or "[]"),
        "url": n.url,
        "summary": n.summary,
        "created_at": n.created_at,
    }


@router.get("")
def list_news(
    company_id: int | None = None,
    category: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(NewsHeadline)
    if company_id:
        q = q.filter(NewsHeadline.company_id == company_id)
    if category:
        q = q.filter(NewsHeadline.category == category)
    if from_date:
        q = q.filter(NewsHeadline.date_of_article >= from_date)
    if to_date:
        q = q.filter(NewsHeadline.date_of_article <= to_date)
    if search:
        q = q.filter(
            NewsHeadline.news_headline.ilike(f"%{search}%")
            | NewsHeadline.summary.ilike(f"%{search}%")
            | NewsHeadline.company_name.ilike(f"%{search}%")
        )
    return [_news_dict(n) for n in q.order_by(NewsHeadline.date_of_article.desc()).all()]


class NewsSearchRequest(BaseModel):
    company_name: str


@router.post("/search")
async def search_news(req: NewsSearchRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    job = ResearchJob(
        job_type="news_search",
        status="pending",
        target=req.company_name,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id

    async def _run():
        from backend.ai_research import search_company_news
        from backend.database import SessionLocal
        from backend.models import Company

        inner_db = SessionLocal()
        try:
            j = inner_db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if j:
                j.status = "running"
                j.updated_at = datetime.now(timezone.utc).isoformat()
                inner_db.commit()

            articles = await asyncio.get_event_loop().run_in_executor(
                None, search_company_news, req.company_name
            )

            company = inner_db.query(Company).filter(
                Company.company_name.ilike(req.company_name)
            ).first()

            ts = datetime.now(timezone.utc).isoformat()
            for article in articles:
                article["company_id"] = company.id if company else None
                article["created_at"] = ts
                for list_field in ("partners", "topics"):
                    if isinstance(article.get(list_field), list):
                        article[list_field] = json.dumps(article[list_field])
                valid = {k: v for k, v in article.items()
                         if k in NewsHeadline.__table__.columns.keys()}
                inner_db.add(NewsHeadline(**valid))
            inner_db.commit()

            j = inner_db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if j:
                j.status = "complete"
                j.result = json.dumps({"news_count": len(articles)})
                j.updated_at = datetime.now(timezone.utc).isoformat()
                inner_db.commit()
        except Exception as e:
            log.error("News search job %d failed: %s", job_id, e)
            j = inner_db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if j:
                j.status = "failed"
                j.result = str(e)
                j.updated_at = datetime.now(timezone.utc).isoformat()
                inner_db.commit()
        finally:
            inner_db.close()

    asyncio.create_task(_run())
    return {"job_id": job_id}
