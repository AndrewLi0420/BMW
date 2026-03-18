"""
Loader — persist validated Pydantic objects into the SQL database.

Handles:
  • Upsert logic for facilities (deduplication via composite key)
  • News insertion with company_id FK resolution
"""

from __future__ import annotations

import json
import logging
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select

from db.models import BatteryFacility, BatteryIndustryNews
from schemas import FacilitySchema, NewsSchema

logger = logging.getLogger(__name__)


def upsert_facilities(
    session: Session, facilities: Sequence[FacilitySchema]
) -> dict[str, int]:
    """
    Insert or update facility records.

    Deduplication key: (company, facility_name, facility_city).

    Returns a dict with counts: {"inserted": N, "updated": M, "skipped": K}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    for fac in facilities:
        try:
            existing = session.execute(
                select(BatteryFacility).where(
                    BatteryFacility.company == fac.company,
                    BatteryFacility.facility_name == fac.facility_name,
                    BatteryFacility.facility_city == fac.facility_city,
                )
            ).scalar_one_or_none()

            data = fac.model_dump()
            if isinstance(data.get("citations"), list):
                data["citations"] = json.dumps(data["citations"])

            if existing:
                # Update all fields except the PK
                for field, value in data.items():
                    if value is not None:
                        setattr(existing, field, value)
                stats["updated"] += 1
                logger.debug("Updated facility: %s / %s", fac.company, fac.facility_name)
            else:
                new_record = BatteryFacility(**data)
                session.add(new_record)
                stats["inserted"] += 1
                logger.debug("Inserted facility: %s / %s", fac.company, fac.facility_name)

        except Exception as exc:
            stats["skipped"] += 1
            logger.warning(
                "Skipped facility %s / %s — %s",
                fac.company,
                fac.facility_name,
                exc,
            )

    session.commit()
    logger.info(
        "Facility upsert complete: %d inserted, %d updated, %d skipped",
        stats["inserted"],
        stats["updated"],
        stats["skipped"],
    )
    return stats


def insert_news(
    session: Session, news_items: Sequence[NewsSchema]
) -> dict[str, int]:
    """
    Insert news records, resolving company_name → company_id via the
    battery_facilities_full table.

    Returns a dict with counts: {"inserted": N, "skipped": K}
    """
    stats = {"inserted": 0, "skipped": 0}

    for item in news_items:
        try:
            # Find facility by company name (first match)
            facility = session.execute(
                select(BatteryFacility).where(
                    BatteryFacility.company == item.company_name
                )
            ).scalars().first()

            if not facility:
                logger.warning(
                    "No matching facility for company '%s' — skipping news: %s",
                    item.company_name,
                    item.headline[:60],
                )
                stats["skipped"] += 1
                continue

            # Check for duplicate news (same headline + company)
            existing_news = session.execute(
                select(BatteryIndustryNews).where(
                    BatteryIndustryNews.company_id == facility.id,
                    BatteryIndustryNews.headline == item.headline,
                )
            ).scalar_one_or_none()

            if existing_news:
                logger.debug("Duplicate news skipped: %s", item.headline[:60])
                stats["skipped"] += 1
                continue

            news_record = BatteryIndustryNews(
                company_id=facility.id,
                headline=item.headline,
                summary=item.summary,
                source_url=item.source_url,
                date_published=item.date_published,
            )
            session.add(news_record)
            stats["inserted"] += 1

        except Exception as exc:
            stats["skipped"] += 1
            logger.warning("Skipped news item — %s", exc)

    session.commit()
    logger.info(
        "News insert complete: %d inserted, %d skipped",
        stats["inserted"],
        stats["skipped"],
    )
    return stats
