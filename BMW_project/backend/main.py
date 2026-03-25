#!/usr/bin/env python3
"""
main.py — CLI entry point for the Battery Industry Data Pipeline.

Usage
-----
    # Full run (all segments) → writes output/battery_pipeline.json
    python main.py

    # Specific segments only
    python main.py --segments "Cell Manufacturing" "Recycling"

    # Custom output path
    python main.py --output /tmp/my_run.json

    # Run pipeline AND validate all cited sources when done
    python main.py --validate-sources

    # Dry run (print extracted data, do NOT write to disk)
    python main.py --dry-run

    # Skip news search phase
    python main.py --no-news
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import Sequence
from pathlib import Path

from config import SUPPLY_CHAIN_SEGMENTS
from api.perplexity_client import GeminiClient
from pipeline.extractor import extract_facilities, extract_news
from pipeline.writer import write_pipeline_output, DEFAULT_OUTPUT_PATH
from pipeline.source_validator import validate_sources

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
    output_path: Path | None = None,
    run_source_validation: bool = False,
) -> None:
    """
    Execute the full pipeline:

    1. For each supply-chain segment → search Gemini → extract → collect.
    2. For each company found → search news → extract → collect.
    3. Write all results to a JSON file (unless dry-run).
    4. Optionally validate all cited sources.
    """
    client = GeminiClient()
    target_segments = list(segments) if segments else SUPPLY_CHAIN_SEGMENTS

    all_facilities = []
    all_news = []
    all_companies: set[str] = set()

    # ── Phase 1: Facilities ───────────────────────────────────────────────────
    for seg in target_segments:
        logger.info("━━━ Searching segment: %s ━━━", seg)
        try:
            raw = client.search_facilities(seg)
            facilities = extract_facilities(raw)

            if dry_run:
                print(f"\n── {seg} ({len(facilities)} facilities) ──")
                for f in facilities:
                    print(json.dumps(f.model_dump(mode="json"), indent=2, default=str))
            else:
                all_facilities.extend(facilities)

            for f in facilities:
                all_companies.add(f.company)

        except Exception as exc:
            logger.error("Failed on segment '%s': %s", seg, exc)

    # ── Phase 2: News ─────────────────────────────────────────────────────────
    if search_news_flag:
        logger.info("━━━ Searching news for %d companies ━━━", len(all_companies))
        for company in sorted(all_companies):
            try:
                raw = client.search_news(company)
                news_items = extract_news(raw)

                if dry_run:
                    print(f"\n── News: {company} ({len(news_items)} articles) ──")
                    for n in news_items:
                        print(json.dumps(n.model_dump(mode="json"), indent=2, default=str))
                else:
                    all_news.extend(news_items)

            except Exception as exc:
                logger.error("Failed news search for '%s': %s", company, exc)

    # ── Phase 3: Write JSON ───────────────────────────────────────────────────
    written_path: Path | None = None
    if not dry_run:
        written_path = write_pipeline_output(
            facilities=all_facilities,
            news=all_news,
            output_path=output_path,
            metadata={"segments": target_segments},
        )

    # ── Phase 4: Source validation (optional) ─────────────────────────────────
    if run_source_validation and not dry_run and written_path:
        logger.info("━━━ Running source validation ━━━")
        data = json.loads(written_path.read_text(encoding="utf-8"))
        data = validate_sources(data)
        written_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  Pipeline Run Complete")
    print("═" * 60)
    print(f"  Segments processed : {len(target_segments)}")
    print(f"  Facilities found   : {len(all_facilities)}")
    print(f"  Companies found    : {len(all_companies)}")
    print(f"  News articles found: {len(all_news)}")
    if dry_run:
        print("  Mode               : DRY RUN (nothing written to disk)")
    else:
        print(f"  Output file        : {written_path or output_path or DEFAULT_OUTPUT_PATH}")
        if run_source_validation:
            print("  Source validation  : complete (see citations_validation in JSON)")
    print("═" * 60 + "\n")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Battery Industry Data Pipeline — search, extract, store as JSON.",
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
        "--output",
        default=None,
        help=(
            "Path for the output JSON file "
            f"(default: {DEFAULT_OUTPUT_PATH})"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print extracted data without writing to disk.",
    )
    parser.add_argument(
        "--no-news",
        action="store_true",
        help="Skip the news-search phase.",
    )
    parser.add_argument(
        "--validate-sources",
        action="store_true",
        help="After writing the JSON, validate all cited source URLs.",
    )
    args = parser.parse_args()

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
        output_path=Path(args.output) if args.output else None,
        run_source_validation=args.validate_sources,
    )


if __name__ == "__main__":
    main()
