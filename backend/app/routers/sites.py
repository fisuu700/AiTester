"""Gestion des sites surveillés et de leur planification."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.db import get_db
from app.models import Scan, Schedule, Site, User
from app.safety import TargetNotAllowed, assert_target_allowed
from app.scan_orchestrator import RUNNER, create_scan
from app.schemas import (
    HistoryPoint,
    ScanCreate,
    ScanSummary,
    ScheduleCreate,
    ScheduleOut,
    SiteCreate,
    SiteOut,
)
from app.serializers import scan_summary, site_out

router = APIRouter(prefix="/api/sites", tags=["sites"])


def _owned_site(db: Session, site_id: int, user: User) -> Site:
    site = db.get(Site, site_id)
    if site is None or site.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Site introuvable.")
    return site


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(
    payload: SiteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteOut:
    if not payload.consent:
        raise HTTPException(
            status_code=400,
            detail="Vous devez certifier être propriétaire du site ou disposer d'une autorisation.",
        )

    try:
        url = assert_target_allowed(payload.url)
    except TargetNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = db.scalar(select(Site).where(Site.owner_id == user.id, Site.url == url))
    if existing:
        raise HTTPException(status_code=409, detail="Ce site est déjà dans votre liste.")

    site = Site(
        owner_id=user.id,
        url=url,
        name=(payload.name or "").strip() or url,
        verified=True,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site_out(site)


@router.get("", response_model=list[SiteOut])
def list_sites(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SiteOut]:
    sites = db.scalars(
        select(Site)
        .where(Site.owner_id == user.id)
        .options(selectinload(Site.scans).selectinload(Scan.findings))
        .order_by(Site.created_at.desc())
    ).all()
    return [site_out(site) for site in sites]


@router.get("/{site_id}", response_model=SiteOut)
def get_site(
    site_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteOut:
    site = _owned_site(db, site_id, user)
    return site_out(site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    site_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    site = _owned_site(db, site_id, user)
    db.delete(site)
    db.commit()


@router.post("/{site_id}/scans", response_model=ScanSummary, status_code=status.HTTP_202_ACCEPTED)
async def launch_scan(
    site_id: int,
    payload: ScanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanSummary:
    site = _owned_site(db, site_id, user)

    running = db.scalar(
        select(Scan)
        .where(Scan.site_id == site.id, Scan.status.in_(("queued", "running")))
        .limit(1)
    )
    if running:
        raise HTTPException(status_code=409, detail="Un scan est déjà en cours pour ce site.")

    scan = create_scan(db, site, mode=payload.mode, scenario=payload.scenario)
    RUNNER.start(scan.id)
    return scan_summary(scan)


@router.get("/{site_id}/history", response_model=list[HistoryPoint])
def history(
    site_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HistoryPoint]:
    site = _owned_site(db, site_id, user)
    scans = db.scalars(
        select(Scan)
        .where(Scan.site_id == site.id, Scan.status == "completed")
        .order_by(Scan.created_at.asc())
        .limit(60)
    ).all()
    return [
        HistoryPoint(
            scan_id=scan.id,
            created_at=scan.created_at,
            global_score=scan.global_score,
            reliability_score=scan.reliability_score,
            security_score=scan.security_score,
            performance_score=scan.performance_score,
            accessibility_score=scan.accessibility_score,
        )
        for scan in scans
    ]


# ---------------------------------------------------------------------------
# Planification
# ---------------------------------------------------------------------------


@router.post("/{site_id}/schedule", response_model=ScheduleOut)
def upsert_schedule(
    site_id: int,
    payload: ScheduleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleOut:
    from app.scheduler import sync_schedule

    site = _owned_site(db, site_id, user)
    schedule = db.scalar(select(Schedule).where(Schedule.site_id == site.id).limit(1))
    if schedule is None:
        schedule = Schedule(site_id=site.id)
        db.add(schedule)

    cron = payload.cron.strip()
    try:
        CronTrigger.from_crontab(cron)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Expression cron invalide : {exc}",
        ) from exc

    schedule.cron = cron
    schedule.mode = payload.mode
    schedule.scenario = payload.scenario
    schedule.enabled = payload.enabled
    db.commit()
    db.refresh(schedule)

    sync_schedule(schedule)
    return ScheduleOut(
        id=schedule.id,
        site_id=schedule.site_id,
        cron=schedule.cron,
        mode=schedule.mode,
        scenario=schedule.scenario,
        enabled=schedule.enabled,
        last_run=schedule.last_run,
    )


@router.get("/{site_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(
    site_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScheduleOut]:
    site = _owned_site(db, site_id, user)
    schedules = db.scalars(select(Schedule).where(Schedule.site_id == site.id)).all()
    return [
        ScheduleOut(
            id=schedule.id,
            site_id=schedule.site_id,
            cron=schedule.cron,
            mode=schedule.mode,
            scenario=schedule.scenario,
            enabled=schedule.enabled,
            last_run=schedule.last_run,
        )
        for schedule in schedules
    ]


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    from app.scheduler import remove_schedule

    schedule = db.get(Schedule, schedule_id)
    if schedule is None or schedule.site.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Planification introuvable.")
    remove_schedule(schedule_id)
    db.delete(schedule)
    db.commit()
