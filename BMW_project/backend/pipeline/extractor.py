"""
Extractor — parse raw LLM responses into validated Pydantic objects.

Handles:
  • JSON extraction from potentially messy LLM output
  • Per-record validation (invalid records are logged and skipped)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from schemas import FacilitySchema, NewsSchema

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> list[dict[str, Any]]:
    """
    Best-effort extraction of a JSON array from a raw string.
    Handles cases where the LLM wraps JSON in markdown fences.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.strip().rstrip("`")

    # Try parsing as-is
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array inside the text
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.error("Failed to extract JSON from LLM response:\n%s", raw[:500])
    return []


def extract_facilities(raw_response: str) -> list[FacilitySchema]:
    """
    Parse LLM output → list of validated FacilitySchema objects.
    Invalid records are logged and skipped.
    """
    records = _extract_json(raw_response)
    facilities: list[FacilitySchema] = []

    for i, rec in enumerate(records):
        try:
            facility = FacilitySchema(**rec)
            facilities.append(facility)
        except Exception as exc:
            logger.warning(
                "Skipping facility record %d — validation error: %s | data=%s",
                i,
                exc,
                json.dumps(rec, default=str)[:300],
            )

    logger.info(
        "Extracted %d valid facilities out of %d raw records",
        len(facilities),
        len(records),
    )
    return facilities


def extract_verification(raw_response: str) -> dict[str, dict]:
    """
    Parse Gemini's fact-check response into a lookup dict keyed by company name.
    Each value has: verification_status ("Verified"/"Uncertain"/"Unverified") and verification_notes.
    """
    records = _extract_json(raw_response)
    result: dict[str, dict] = {}
    for rec in records:
        company = rec.get("company")
        if not company:
            continue
        exists = bool(rec.get("exists", False))
        battery_related = bool(rec.get("battery_related", False))
        if exists and battery_related:
            status = "Verified"
        elif not exists:
            status = "Unverified"
        else:
            status = "Uncertain"
        result[company] = {
            "verification_status": status,
            "verification_notes": rec.get("verification_notes", ""),
        }
    logger.info("Verified %d companies", len(result))
    return result


def extract_news(raw_response: str) -> list[NewsSchema]:
    """
    Parse LLM output → list of validated NewsSchema objects.
    Invalid records are logged and skipped.
    """
    records = _extract_json(raw_response)
    news_items: list[NewsSchema] = []

    for i, rec in enumerate(records):
        try:
            item = NewsSchema(**rec)
            news_items.append(item)
        except Exception as exc:
            logger.warning(
                "Skipping news record %d — validation error: %s | data=%s",
                i,
                exc,
                json.dumps(rec, default=str)[:300],
            )

    logger.info(
        "Extracted %d valid news items out of %d raw records",
        len(news_items),
        len(records),
    )
    return news_items
