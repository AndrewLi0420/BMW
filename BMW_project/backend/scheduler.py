#!/usr/bin/env python3
"""
scheduler.py — Run the battery pipeline on a weekly schedule.

Usage
-----
    # Start the scheduler (runs indefinitely)
    python scheduler.py

    # Alternatively, use a system cron job:
    # crontab -e
    # 0 8 * * 1  cd /path/to/BMW_project && /path/to/python main.py >> pipeline.log 2>&1
"""

from __future__ import annotations

import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import schedule

from main import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler")


def job() -> None:
    """Wrapper for the scheduled pipeline run."""
    logger.info("Scheduled pipeline run starting…")
    try:
        run_pipeline()
        logger.info("Scheduled pipeline run completed successfully.")
    except Exception as exc:
        logger.error("Scheduled pipeline run FAILED: %s", exc)


def main() -> None:
    # Schedule: every Monday at 08:00
    schedule.every().monday.at("08:00").do(job)

    logger.info("Scheduler started. Pipeline will run every Monday at 08:00.")
    logger.info("Press Ctrl+C to stop.")

    # Run once immediately on start, then follow the schedule
    job()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
