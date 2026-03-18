#!/usr/bin/env python3
"""
server.py — FastAPI backend for the BMW Battery Intelligence frontend.

Endpoints
---------
  GET  /api/segments          → list of supply-chain segments
  POST /api/run               → run pipeline for a segment, return facility details + credibility data
  GET  /api/download-csv      → download facilities for a segment as CSV

Usage
-----
    source venv/bin/activate
    pip install fastapi uvicorn
    python server.py
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Ensure project root is on the path so local modules resolve
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import SUPPLY_CHAIN_SEGMENTS
from db.models import init_db, get_session, BatteryFacility
from api.perplexity_client import GeminiClient
from pipeline.extractor import extract_facilities, extract_verification
from pipeline.loader import upsert_facilities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("server")

app = FastAPI(title="BMW Battery Intelligence API")

# Allow the Vite dev server (port 5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise DB tables on startup
init_db()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_website(url: str | None) -> bool | None:
    """HTTP HEAD check to verify a company website is reachable."""
    if not url:
        return None
    try:
        req = urllib.request.Request(str(url), method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status < 400
    except Exception:
        return False


# ── Request / Response models ────────────────────────────────────────────────

class RunRequest(BaseModel):
    segment: str


class FacilityOut(BaseModel):
    id: int
    company: str
    facility_name: Optional[str] = None
    facility_city: Optional[str] = None
    facility_state_or_province: Optional[str] = None
    supply_chain_segment: str
    status: Optional[str] = None
    company_website: Optional[str] = None
    confidence_score: Optional[int] = None
    citations: Optional[list] = None
    citations_ok: Optional[list] = None   # parallel bool list — True/False/None per citation
    website_reachable: Optional[bool] = None
    verification_status: Optional[str] = None


class RunResponse(BaseModel):
    segment: str
    facilities_found: int
    status: str
    facilities: list[FacilityOut]


# ── CSV column order ─────────────────────────────────────────────────────────

CSV_COLUMNS = [
    "id",
    "status",
    "supply_chain_segment",
    "company",
    "company_website",
    "naatbatt_member",
    "hq_city",
    "hq_state",
    "facility_name",
    "product_facility_type",
    "product",
    "facility_address",
    "facility_city",
    "facility_state_or_province",
    "facility_country",
    "facility_zip",
    "facility_phone",
    "latitude",
    "longitude",
    "confidence_score",
    "citations",
    "website_reachable",
    "verification_status",
]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/segments")
def get_segments() -> list[str]:
    """Return the list of all supply-chain segments."""
    return SUPPLY_CHAIN_SEGMENTS


@app.post("/api/run", response_model=RunResponse)
def run_segment(body: RunRequest) -> RunResponse:
    """
    Run the pipeline for a single segment with three credibility layers:
      1. Gemini returns confidence_score + citations per facility
      2. A second Gemini call verifies each company exists and is battery-related
      3. HTTP HEAD checks on company websites for reachability
    """
    if body.segment not in SUPPLY_CHAIN_SEGMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown segment '{body.segment}'. "
                   f"Valid options: {SUPPLY_CHAIN_SEGMENTS}",
        )

    logger.info("Running pipeline for segment: %s", body.segment)
    client = GeminiClient()

    # Phase 1: Fetch and extract facilities (confidence + citations come from Gemini)
    try:
        raw = client.search_facilities(body.segment)
        facilities = extract_facilities(raw)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    # Phase 2: Gemini fact-check verification pass
    verification: dict = {}
    if facilities:
        companies = list({f.company for f in facilities})
        try:
            raw_verify = client.verify_facilities(body.segment, companies)
            verification = extract_verification(raw_verify)
        except Exception as exc:
            logger.warning("Verification pass failed (continuing without it): %s", exc)

        # Apply verification_status to each facility schema object
        for fac in facilities:
            v = verification.get(fac.company)
            if v:
                fac.verification_status = v["verification_status"]

    # Phase 3: Concurrent website reachability checks
    if facilities:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {fac.company: executor.submit(_check_website, fac.company_website)
                       for fac in facilities}
        for fac in facilities:
            fac.website_reachable = futures[fac.company].result()

    # Upsert to DB (loader handles citations JSON encoding)
    session = get_session()
    try:
        upsert_facilities(session, facilities)
    finally:
        session.close()

    # Query saved rows to get IDs and build response
    session = get_session()
    try:
        rows = (
            session.query(BatteryFacility)
            .filter(BatteryFacility.supply_chain_segment == body.segment)
            .all()
        )

        # Decode citations for all rows first
        rows_citations: list[list[str] | None] = []
        for row in rows:
            decoded = None
            if row.citations:
                try:
                    decoded = json.loads(row.citations)
                except Exception:
                    decoded = [row.citations]
            rows_citations.append(decoded)

        # Collect all unique citation URLs and check them concurrently
        all_citation_urls: set[str] = set()
        for clist in rows_citations:
            if clist:
                for c in clist:
                    if isinstance(c, str) and c.startswith("http"):
                        all_citation_urls.add(c)

        citation_status: dict[str, bool | None] = {}
        if all_citation_urls:
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures_map = {url: executor.submit(_check_website, url) for url in all_citation_urls}
            citation_status = {url: f.result() for url, f in futures_map.items()}

        facility_out: list[FacilityOut] = []
        for row, citations_decoded in zip(rows, rows_citations):
            # Filter out broken citation URLs
            if citations_decoded:
                valid_citations = [
                    c for c in citations_decoded
                    if not (isinstance(c, str) and c.startswith("http") and citation_status.get(c) is False)
                ]
            else:
                valid_citations = citations_decoded

            # If all citations were invalidated, remove the facility entirely
            if not valid_citations:
                session.delete(row)
                continue

            if valid_citations != citations_decoded:
                row.citations = json.dumps(valid_citations)

            facility_out.append(FacilityOut(
                id=row.id,
                company=row.company,
                facility_name=row.facility_name,
                facility_city=row.facility_city,
                facility_state_or_province=row.facility_state_or_province,
                supply_chain_segment=row.supply_chain_segment,
                status=row.status,
                company_website=row.company_website,
                confidence_score=row.confidence_score,
                citations=valid_citations,
                citations_ok=None,
                website_reachable=row.website_reachable,
                verification_status=row.verification_status,
            ))
        session.commit()
    finally:
        session.close()

    logger.info("Pipeline complete — %d facilities for '%s'", len(facility_out), body.segment)
    return RunResponse(
        segment=body.segment,
        facilities_found=len(facility_out),
        status="ok",
        facilities=facility_out,
    )


@app.get("/api/download-csv")
def download_csv(segment: str) -> StreamingResponse:
    """
    Stream a CSV of all facilities for the given segment.
    """
    if segment not in SUPPLY_CHAIN_SEGMENTS:
        raise HTTPException(status_code=400, detail=f"Unknown segment '{segment}'.")

    session = get_session()
    rows = (
        session.query(BatteryFacility)
        .filter(BatteryFacility.supply_chain_segment == segment)
        .all()
    )
    session.close()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow({col: getattr(row, col, None) for col in CSV_COLUMNS})

    output.seek(0)
    filename = segment.lower().replace(" ", "_").replace("&", "and") + "_facilities.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
