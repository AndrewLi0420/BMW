"""
Sync data from the BMW_project pipeline DB (battery_pipeline.db) into
the BMW_Visualizer DB (battery_intel.db).

POST /api/sync/pipeline
  - Reads battery_facilities_full  → upserts into companies
  - Reads battery_industry_news    → upserts into news_headlines
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import PIPELINE_DB_PATH
from backend.database import get_db
from backend.models import Company, NewsHeadline, SyncLog

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


def _open_pipeline_db(path: str) -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Cannot open pipeline DB at {path!r}: {exc}",
        )


def _sync_facilities(pipeline_conn: sqlite3.Connection, db: Session, ts: str) -> tuple[int, int]:
    """Map battery_facilities_full rows → Company and upsert. Returns (added, updated)."""
    rows = pipeline_conn.execute(
        "SELECT * FROM battery_facilities_full"
    ).fetchall()

    added = updated = 0
    for row in rows:
        name = (row["company"] or "").strip()
        if not name:
            continue

        existing = db.query(Company).filter(
            Company.company_name.ilike(name)
        ).first()

        # Build a facility location entry for company_locations
        facility_loc = {
            "name": row["facility_name"] or "",
            "address": row["facility_address"] or "",
            "city": row["facility_city"] or "",
            "state": row["facility_state_or_province"] or "",
            "country": row["facility_country"] or "",
            "zip": row["facility_zip"] or "",
            "lat": row["latitude"],
            "lng": row["longitude"],
            "product": row["product"] or "",
            "type": row["product_facility_type"] or "",
        }

        if existing:
            # Merge facility into company_locations list
            locs: list = []
            if existing.company_locations:
                try:
                    locs = json.loads(existing.company_locations)
                except Exception:
                    locs = []
            # Deduplicate by facility name + city
            key = (facility_loc["name"].lower(), facility_loc["city"].lower())
            if not any(
                (l.get("name", "").lower(), l.get("city", "").lower()) == key
                for l in locs
            ):
                locs.append(facility_loc)
                existing.company_locations = json.dumps(locs)

            # Only fill in fields that are currently empty
            if not existing.company_hq_city and row["hq_city"]:
                existing.company_hq_city = row["hq_city"]
            if not existing.company_hq_state and row["hq_state"]:
                existing.company_hq_state = row["hq_state"]
            if not existing.company_hq_lat and row["latitude"]:
                existing.company_hq_lat = row["latitude"]
                existing.company_hq_lng = row["longitude"]
            if not existing.company_hq_country and row["facility_country"]:
                existing.company_hq_country = row["facility_country"]
            if not existing.supply_chain_segment and row["supply_chain_segment"]:
                existing.supply_chain_segment = row["supply_chain_segment"]
            if not existing.company_status and row["status"]:
                existing.company_status = row["status"]
            if not existing.company_website and row["company_website"]:
                existing.company_website = row["company_website"]
            if row["naatbatt_member"] is not None:
                existing.naatbatt_member = int(bool(row["naatbatt_member"]))
            existing.last_updated = ts
            updated += 1
        else:
            new_company = Company(
                company_name=name,
                company_hq_city=row["hq_city"],
                company_hq_state=row["hq_state"],
                company_hq_country=row["facility_country"],
                company_hq_lat=row["latitude"],
                company_hq_lng=row["longitude"],
                supply_chain_segment=row["supply_chain_segment"],
                company_status=row["status"],
                company_website=row["company_website"],
                naatbatt_member=int(bool(row["naatbatt_member"])) if row["naatbatt_member"] is not None else 0,
                company_locations=json.dumps([facility_loc]),
                data_source="pipeline_sync",
                last_updated=ts,
            )
            db.add(new_company)
            db.flush()  # get new_company.id
            added += 1

    db.commit()
    return added, updated


def _sync_news(pipeline_conn: sqlite3.Connection, db: Session, ts: str) -> tuple[int, int]:
    """Map battery_industry_news rows → NewsHeadline and upsert. Returns (added, skipped)."""
    rows = pipeline_conn.execute(
        """
        SELECT n.*, f.company AS company_name
        FROM battery_industry_news n
        JOIN battery_facilities_full f ON f.id = n.company_id
        """
    ).fetchall()

    added = skipped = 0
    for row in rows:
        company_name = (row["company_name"] or "").strip()
        headline = (row["headline"] or "").strip()
        if not headline:
            continue

        # Resolve company_id in the Visualizer DB
        company = (
            db.query(Company)
            .filter(Company.company_name.ilike(company_name))
            .first()
        )

        if not company:
            skipped += 1
            continue

        # Deduplicate by company_id + headline
        existing_news = (
            db.query(NewsHeadline)
            .filter(
                NewsHeadline.company_id == company.id,
                NewsHeadline.news_headline == headline,
            )
            .first()
        )
        if existing_news:
            skipped += 1
            continue

        db.add(
            NewsHeadline(
                company_id=company.id,
                company_name=company_name,
                news_headline=headline,
                summary=row["summary"],
                url=row["source_url"],
                date_of_article=str(row["date_published"]) if row["date_published"] else None,
                news_source="pipeline_sync",
                created_at=ts,
            )
        )
        added += 1

    db.commit()
    return added, skipped


@router.post("/pipeline")
def sync_pipeline(db: Session = Depends(get_db)):
    """
    Import facilities and news from the BMW_project pipeline DB into BMW_Visualizer.
    Upserts companies and deduplicates news headlines.
    """
    ts = datetime.now(timezone.utc).isoformat()
    pipeline_conn = _open_pipeline_db(PIPELINE_DB_PATH)

    try:
        companies_added, companies_updated = _sync_facilities(pipeline_conn, db, ts)
        news_added, news_skipped = _sync_news(pipeline_conn, db, ts)
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Pipeline sync failed: %s", exc)
        db.add(SyncLog(
            source="pipeline_sync",
            status="failed",
            rows_added=0,
            rows_updated=0,
            error_message=str(exc),
            run_at=ts,
        ))
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        pipeline_conn.close()

    db.add(SyncLog(
        source="pipeline_sync",
        status="ok",
        rows_added=companies_added + news_added,
        rows_updated=companies_updated,
        error_message=None,
        run_at=ts,
    ))
    db.commit()

    log.info(
        "Pipeline sync complete: %d companies added, %d updated, %d news added, %d news skipped",
        companies_added, companies_updated, news_added, news_skipped,
    )
    return {
        "status": "ok",
        "companies_added": companies_added,
        "companies_updated": companies_updated,
        "news_added": news_added,
        "news_skipped": news_skipped,
    }
