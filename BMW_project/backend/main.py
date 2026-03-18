#!/usr/bin/env python3
"""
main.py — CLI entry point for the Battery Industry Data Pipeline.

Usage
-----
    # Full run (all segments)
    python main.py

    # Specific segments only
    python main.py --segments "Cell Manufacturing" "Recycling"

    # Dry run (print extracted data, do NOT write to DB)
    python main.py --dry-run

    # Combine flags
    python main.py --segments "Anodes" --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import Sequence

from config import SUPPLY_CHAIN_SEGMENTS
from db.models import init_db, get_session, BatteryFacility
from api.perplexity_client import GeminiClient
from pipeline.extractor import extract_facilities, extract_news
from pipeline.loader import upsert_facilities, insert_news
from sqlalchemy import select

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("battery_pipeline")


# ── Pipeline ─────────────────────────────────────────────────────────────────
def run_pipeline(
    segments: Sequence[str] | None = None,
    dry_run: bool = False,
    search_news_flag: bool = True,
) -> None:
    """
    Execute the full pipeline:

    1. Initialise the database.
    2. For each supply-chain segment → search → extract → validate → upsert.
    3. For each company found → search news → extract → insert.
    """
    # 1. Database
    if not dry_run:
        init_db()
        logger.info("Database tables initialised.")

    client = GeminiClient()
    target_segments = segments or SUPPLY_CHAIN_SEGMENTS

    total_facilities = 0
    total_news = 0
    all_companies: set[str] = set()

    # 2. Facilities
    for seg in target_segments:
        logger.info("━━━ Searching segment: %s ━━━", seg)
        try:
            raw = client.search_facilities(seg)
            facilities = extract_facilities(raw)
            total_facilities += len(facilities)

            if dry_run:
                print(f"\n── {seg} ({len(facilities)} facilities) ──")
                for f in facilities:
                    print(json.dumps(f.model_dump(), indent=2, default=str))
            else:
                session = get_session()
                stats = upsert_facilities(session, facilities)
                session.close()
                logger.info("Segment '%s' → %s", seg, stats)

            for f in facilities:
                all_companies.add(f.company)

        except Exception as exc:
            logger.error("Failed on segment '%s': %s", seg, exc)

    # 3. News
    if search_news_flag:
        logger.info("━━━ Searching news for %d companies ━━━", len(all_companies))
        for company in sorted(all_companies):
            try:
                raw = client.search_news(company)
                news_items = extract_news(raw)
                total_news += len(news_items)

                if dry_run:
                    print(f"\n── News: {company} ({len(news_items)} articles) ──")
                    for n in news_items:
                        print(json.dumps(n.model_dump(), indent=2, default=str))
                else:
                    session = get_session()
                    stats = insert_news(session, news_items)
                    session.close()
                    logger.info("News for '%s' → %s", company, stats)

            except Exception as exc:
                logger.error("Failed news search for '%s': %s", company, exc)

    # 4. Summary
    print("\n" + "═" * 60)
    print("  Pipeline Run Complete")
    print("═" * 60)
    print(f"  Segments processed : {len(target_segments)}")
    print(f"  Facilities found   : {total_facilities}")
    print(f"  Companies found    : {len(all_companies)}")
    print(f"  News articles found: {total_news}")
    if dry_run:
        print("  Mode               : DRY RUN (nothing written to DB)")
    else:
        # Quick DB count
        session = get_session()
        fac_count = session.query(BatteryFacility).count()
        session.close()
        print(f"  Total DB facilities: {fac_count}")
    print("═" * 60 + "\n")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Battery Industry Data Pipeline — search, extract, store.",
    )
    parser.add_argument(
        "--segments",
        nargs="+",
        default=None,
        help=(
            "Supply-chain segments to process (default: all). "
            f"Choices: {SUPPLY_CHAIN_SEGMENTS}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print extracted data without writing to the database.",
    )
    parser.add_argument(
        "--no-news",
        action="store_true",
        help="Skip the news-search phase.",
    )
    args = parser.parse_args()

    # Validate segment names
    if args.segments:
        for s in args.segments:
            if s not in SUPPLY_CHAIN_SEGMENTS:
                print(
                    f"Error: unknown segment '{s}'.\n"
                    f"Valid segments: {SUPPLY_CHAIN_SEGMENTS}",
                    file=sys.stderr,
                )
                sys.exit(1)

    run_pipeline(
        segments=args.segments,
        dry_run=args.dry_run,
        search_news_flag=not args.no_news,
    )


if __name__ == "__main__":
    main()
