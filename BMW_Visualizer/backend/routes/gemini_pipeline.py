"""
Pipeline route — proxies requests to BMW_project (port 8001) and stores
results directly into battery_intel.db.

BMW_project owns all pipeline/search/AI logic.
BMW_Visualizer owns the database and display layer.

POST /api/pipeline/run    → call BMW_project, store results
GET  /api/pipeline/segments → forward segment list from BMW_project
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import BMW_PROJECT_URL
from backend.database import get_db
from backend.models import Company, NewsHeadline, SyncLog

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


# ── Response models ───────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    segment: str


class FacilityResult(BaseModel):
    company: str
    facility_name: str | None = None
    facility_city: str | None = None
    supply_chain_segment: str
    status: str | None = None
    confidence_score: int | None = None
    verification_status: str | None = None


class RunResponse(BaseModel):
    segment: str
    companies_added: int
    companies_updated: int
    news_added: int
    facilities: list[FacilityResult]


# ── DB helpers ────────────────────────────────────────────────────────────────

def _upsert_facilities(facilities: list[dict], db: Session, ts: str) -> tuple[int, int, list[FacilityResult]]:
    added = updated = 0
    results: list[FacilityResult] = []

    for fac in facilities:
        name = (fac.get("company") or "").strip()
        if not name:
            continue

        existing = db.query(Company).filter(Company.company_name.ilike(name)).first()

        facility_loc = {
            "name": fac.get("facility_name") or "",
            "city": fac.get("facility_city") or "",
            "state": fac.get("facility_state_or_province") or "",
            "country": fac.get("facility_country") or "",
            "zip": fac.get("facility_zip") or "",
            "lat": fac.get("latitude"),
            "lng": fac.get("longitude"),
            "product": fac.get("product") or "",
            "type": fac.get("product_facility_type") or "",
        }

        if existing:
            locs: list = []
            if existing.company_locations:
                try:
                    locs = json.loads(existing.company_locations)
                except Exception:
                    locs = []
            key = (facility_loc["name"].lower(), facility_loc["city"].lower())
            if not any((l.get("name", "").lower(), l.get("city", "").lower()) == key for l in locs):
                locs.append(facility_loc)
                existing.company_locations = json.dumps(locs)

            if not existing.company_hq_city and fac.get("hq_city"):
                existing.company_hq_city = fac["hq_city"]
            if not existing.company_hq_state and fac.get("hq_state"):
                existing.company_hq_state = fac["hq_state"]
            if not existing.company_hq_country and fac.get("facility_country"):
                existing.company_hq_country = fac["facility_country"]
            if not existing.company_hq_lat and fac.get("latitude"):
                existing.company_hq_lat = fac["latitude"]
                existing.company_hq_lng = fac.get("longitude")
            if not existing.supply_chain_segment and fac.get("supply_chain_segment"):
                existing.supply_chain_segment = fac["supply_chain_segment"]
            if not existing.company_status and fac.get("status"):
                existing.company_status = fac["status"]
            if not existing.company_website and fac.get("company_website"):
                existing.company_website = fac["company_website"]
            if fac.get("naatbatt_member") is not None:
                existing.naatbatt_member = int(bool(fac["naatbatt_member"]))
            existing.last_updated = ts
            updated += 1
        else:
            db.add(Company(
                company_name=name,
                company_hq_city=fac.get("hq_city"),
                company_hq_state=fac.get("hq_state"),
                company_hq_country=fac.get("facility_country"),
                company_hq_lat=fac.get("latitude"),
                company_hq_lng=fac.get("longitude"),
                supply_chain_segment=fac.get("supply_chain_segment"),
                company_status=fac.get("status"),
                company_website=fac.get("company_website"),
                naatbatt_member=int(bool(fac.get("naatbatt_member"))) if fac.get("naatbatt_member") is not None else 0,
                company_locations=json.dumps([facility_loc]),
                data_source="bmw_project_pipeline",
                last_updated=ts,
            ))
            db.flush()
            added += 1

        results.append(FacilityResult(
            company=name,
            facility_name=fac.get("facility_name"),
            facility_city=fac.get("facility_city"),
            supply_chain_segment=fac.get("supply_chain_segment", ""),
            status=fac.get("status"),
            confidence_score=fac.get("confidence_score"),
            verification_status=fac.get("verification_status"),
        ))

    db.commit()
    return added, updated, results


def _upsert_news(news_items: list[dict], db: Session, ts: str) -> int:
    added = 0
    for item in news_items:
        company_name = (item.get("company_name") or "").strip()
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue

        company = db.query(Company).filter(Company.company_name.ilike(company_name)).first()
        if not company:
            continue

        exists = (
            db.query(NewsHeadline)
            .filter(NewsHeadline.company_id == company.id, NewsHeadline.news_headline == headline)
            .first()
        )
        if exists:
            continue

        db.add(NewsHeadline(
            company_id=company.id,
            company_name=company_name,
            news_headline=headline,
            summary=item.get("summary"),
            url=item.get("source_url"),
            date_of_article=str(item["date_published"]) if item.get("date_published") else None,
            news_source="bmw_project_pipeline",
            created_at=ts,
        ))
        added += 1

    db.commit()
    return added


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/segments")
async def get_segments():
    """Forward segment list from BMW_project."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{BMW_PROJECT_URL}/api/segments")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"BMW_project unavailable: {exc}")


@router.post("/run", response_model=RunResponse)
async def run_pipeline(body: RunRequest, db: Session = Depends(get_db)):
    """
    Call BMW_project pipeline for the given segment, then store results in battery_intel.db.
    BMW_project handles all Gemini search and verification logic.
    """
    ts = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(timeout=300) as client:
        try:
            resp = await client.post(
                f"{BMW_PROJECT_URL}/api/run",
                json={"segment": body.segment},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"BMW_project unavailable: {exc}")

    facilities = data.get("facilities", [])
    news_items = data.get("news", [])

    companies_added, companies_updated, results = _upsert_facilities(facilities, db, ts)
    news_added = _upsert_news(news_items, db, ts)

    db.add(SyncLog(
        source="bmw_project_pipeline",
        status="ok",
        rows_added=companies_added + news_added,
        rows_updated=companies_updated,
        error_message=None,
        run_at=ts,
    ))
    db.commit()

    log.info(
        "Pipeline stored: %d added, %d updated, %d news for '%s'",
        companies_added, companies_updated, news_added, body.segment,
    )
    return RunResponse(
        segment=body.segment,
        companies_added=companies_added,
        companies_updated=companies_updated,
        news_added=news_added,
        facilities=results,
    )
