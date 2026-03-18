"""
Pydantic validation schemas for data extracted from the Perplexity API.

Every record coming out of the LLM is validated here before it touches
the database.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, field_validator, HttpUrl

from config import SUPPLY_CHAIN_SEGMENTS


# ── Facility Schema ─────────────────────────────────────────────────────────
class FacilitySchema(BaseModel):
    """Validates a single battery facility record."""

    status: Optional[str] = None
    supply_chain_segment: str
    company: str
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
    facility_phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence_score: Optional[int] = None      # 0-100, Gemini self-reported
    citations: Optional[List[str]] = None        # source names from Gemini
    website_reachable: Optional[bool] = None     # set by server after HTTP check
    verification_status: Optional[str] = None    # "Verified"/"Uncertain"/"Unverified"

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("supply_chain_segment")
    @classmethod
    def validate_segment(cls, v: str) -> str:
        # Exact match first
        if v in SUPPLY_CHAIN_SEGMENTS:
            return v
        # Case-insensitive fallback — LLMs sometimes change capitalisation
        v_lower = v.strip().lower()
        for seg in SUPPLY_CHAIN_SEGMENTS:
            if seg.lower() == v_lower:
                return seg
        raise ValueError(
            f"Invalid supply chain segment: '{v}'. "
            f"Must be one of {SUPPLY_CHAIN_SEGMENTS}"
        )

    @field_validator("facility_zip")
    @classmethod
    def validate_zip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Accept 5-digit or 5+4 US zip, or generic alphanumeric postal codes
        pattern = r"^\d{5}(-\d{4})?$|^[A-Za-z0-9\s\-]{3,10}$"
        if not re.match(pattern, v.strip()):
            raise ValueError(f"Invalid zip/postal code format: '{v}'")
        return v.strip()

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < -90 or v > 90):
            raise ValueError(f"Latitude must be in [-90, 90], got {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < -180 or v > 180):
            raise ValueError(f"Longitude must be in [-180, 180], got {v}")
        return v

    @field_validator("company_website")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        # Basic URL check — allow with or without scheme
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        # Let Pydantic's HttpUrl do heavy lifting
        try:
            HttpUrl(v)
        except Exception:
            raise ValueError(f"Invalid URL: '{v}'")
        return v


# ── News Schema ──────────────────────────────────────────────────────────────
class NewsSchema(BaseModel):
    """Validates a single battery industry news record."""

    company_name: str  # used to look up company_id in the DB
    headline: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    date_published: Optional[date] = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        try:
            HttpUrl(v)
        except Exception:
            raise ValueError(f"Invalid source URL: '{v}'")
        return v

    @field_validator("date_published", mode="before")
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return v
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # Try common formats
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    from datetime import datetime
                    return datetime.strptime(v.strip(), fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Cannot parse date: '{v}'")
        return v
