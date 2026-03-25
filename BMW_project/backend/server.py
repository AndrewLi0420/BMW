#!/usr/bin/env python3
"""
server.py — BMW_project pipeline API server (port 8001).

BMW_project is the backend pipeline. It owns all Gemini search, extraction,
and verification logic. BMW_Visualizer calls this API and stores the results.

Endpoints
---------
  GET  /api/segments   → list of supply-chain segments
  POST /api/run        → run pipeline for a segment, return structured data
"""

from __future__ import annotations

import logging
import sys
import os
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from config import SUPPLY_CHAIN_SEGMENTS
from api.perplexity_client import GeminiClient
from pipeline.extractor import extract_facilities, extract_verification, extract_news

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bmw_project.server")

app = FastAPI(title="BMW Battery Pipeline API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Response models ───────────────────────────────────────────────────────────

class FacilityData(BaseModel):
    company: str
    supply_chain_segment: str
    status: Optional[str] = None
    company_website: Optional[str] = None
    naatbatt_member: bool = False
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    facility_name: Optional[str] = None
    product_facility_type: Optional[str] = None
    product: Optional[str] = None
    facility_address: Optional[str] = None
    facility_city: Optional[str] = None
    facility_state_or_province: Optional[str] = None
    facility_country: Optional[str] = None
    facility_zip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence_score: Optional[int] = None
    citations: Optional[list[str]] = None
    verification_status: Optional[str] = None


class NewsData(BaseModel):
    company_name: str
    headline: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    date_published: Optional[str] = None


class RunRequest(BaseModel):
    segment: str


class RunResponse(BaseModel):
    segment: str
    facilities: list[FacilityData]
    news: list[NewsData]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/segments")
def get_segments() -> list[str]:
    return SUPPLY_CHAIN_SEGMENTS


@app.post("/api/run", response_model=RunResponse)
def run_pipeline(body: RunRequest) -> RunResponse:
    """
    Run the Gemini pipeline for a single segment.

    Phase 1 — Gemini searches for facilities (returns confidence + citations).
    Phase 2 — Gemini fact-checks each company.
    Phase 3 — Gemini searches for recent news on each company.

    Returns structured facility and news data for the Visualizer to store.
    """
    if body.segment not in SUPPLY_CHAIN_SEGMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown segment '{body.segment}'. Valid: {SUPPLY_CHAIN_SEGMENTS}",
        )

    logger.info("Pipeline run: %s", body.segment)
    client = GeminiClient()

    # Phase 1: facility search
    try:
        raw = client.search_facilities(body.segment)
        facilities = extract_facilities(raw)
    except Exception as exc:
        logger.error("Facility search failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    # Phase 2: verification
    if facilities:
        companies = list({f.company for f in facilities})
        try:
            raw_verify = client.verify_facilities(body.segment, companies)
            from pipeline.extractor import extract_verification
            verification = extract_verification(raw_verify)
            for fac in facilities:
                v = verification.get(fac.company)
                if v:
                    fac.verification_status = v["verification_status"]
        except Exception as exc:
            logger.warning("Verification pass skipped: %s", exc)

    # Phase 3: news for each company
    company_names = list({f.company for f in facilities})
    all_news = []
    for company in company_names:
        try:
            raw_news = client.search_news(company)
            all_news.extend(extract_news(raw_news))
        except Exception as exc:
            logger.warning("News search failed for '%s': %s", company, exc)

    logger.info(
        "Pipeline complete: %d facilities, %d news for '%s'",
        len(facilities), len(all_news), body.segment,
    )
    return RunResponse(
        segment=body.segment,
        facilities=[FacilityData(**f.model_dump(mode="json")) for f in facilities],
        news=[NewsData(**n.model_dump(mode="json")) for n in all_news],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
