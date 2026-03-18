"""APScheduler background job for weekly NAATBatt refresh."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_refresh():
    from backend.database import SessionLocal
    from backend.seed import import_naatbatt

    log.info("Scheduled NAATBatt refresh starting…")
    db = SessionLocal()
    try:
        result = import_naatbatt(db, force_download=True)
        log.info("Scheduled refresh complete: %s", result)
    except Exception as e:
        log.error("Scheduled refresh failed: %s", e)
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_refresh,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="naatbatt_weekly_refresh",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("APScheduler started — weekly NAATBatt refresh every Sunday at 02:00.")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_next_run_time() -> str | None:
    if _scheduler is None:
        return None
    job = _scheduler.get_job("naatbatt_weekly_refresh")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
