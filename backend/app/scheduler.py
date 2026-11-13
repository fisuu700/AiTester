"""Planification des scans récurrents (APScheduler)."""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Schedule, Site

_scheduler: AsyncIOScheduler | None = None


def _job_id(schedule_id: int) -> str:
    return f"scan-schedule-{schedule_id}"


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def _add_job(schedule: Schedule) -> None:
    scheduler = get_scheduler()
    try:
        trigger = CronTrigger.from_crontab(schedule.cron)
    except ValueError:
        return
    scheduler.add_job(
        _execute,
        trigger,
        id=_job_id(schedule.id),
        args=[schedule.id],
        replace_existing=True,
        misfire_grace_time=3600,
    )


def sync_schedule(schedule: Schedule) -> None:
    remove_schedule(schedule.id)
    if not schedule.enabled:
        return
    scheduler = get_scheduler()
    if not scheduler.running:
        return
    _add_job(schedule)


def remove_schedule(schedule_id: int) -> None:
    scheduler = get_scheduler()
    if scheduler.get_job(_job_id(schedule_id)):
        scheduler.remove_job(_job_id(schedule_id))


def start_scheduler() -> None:
    db = SessionLocal()
    try:
        schedules = db.scalars(select(Schedule).where(Schedule.enabled.is_(True))).all()
        for schedule in schedules:
            _add_job(schedule)
    finally:
        db.close()

    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def _execute(schedule_id: int) -> None:
    """Job planifié : crée un scan et le démarre."""
    from app.scan_orchestrator import RUNNER, create_scan

    db = SessionLocal()
    try:
        schedule = db.get(Schedule, schedule_id)
        if schedule is None or not schedule.enabled:
            return
        site = db.get(Site, schedule.site_id)
        if site is None:
            return

        scan = create_scan(
            db,
            site,
            mode=schedule.mode,
            scenario=schedule.scenario,
            triggered_by="schedule",
        )
        schedule.last_run = datetime.now(timezone.utc)
        db.commit()
        RUNNER.start(scan.id)
    finally:
        db.close()
