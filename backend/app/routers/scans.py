"""Consultation des scans, streaming temps réel et export de rapports."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_actor, get_current_user, user_from_token
from app.db import SessionLocal, get_db
from app.models import Scan, Site, User
from app.reporting.web import html_to_pdf, render_report_html
from app.safety import TargetNotAllowed, assert_target_allowed
from app.scan_orchestrator import HUB, RUNNER, create_scan
from app.schemas import ApiScanRequest, ScanOut, ScanSummary
from app.serializers import scan_out, scan_summary

router = APIRouter(prefix="/api/scans", tags=["scans"])
ws_router = APIRouter()


def _owned_scan(db: Session, scan_id: str, user: User) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None or scan.site is None or scan.site.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Scan introuvable.")
    return scan


@router.post("", response_model=ScanSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_scan_from_api(
    payload: ApiScanRequest,
    user: User = Depends(get_actor),
    db: Session = Depends(get_db),
) -> ScanSummary:
    """Endpoint CI/CD : lance un scan à partir d'une URL (JWT ou X-API-Key)."""
    try:
        url = assert_target_allowed(payload.url)
    except TargetNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    site = db.scalar(select(Site).where(Site.owner_id == user.id, Site.url == url))
    if site is None:
        site = Site(owner_id=user.id, url=url, name=url, verified=True)
        db.add(site)
        db.commit()
        db.refresh(site)

    scan = create_scan(
        db,
        site,
        mode=payload.mode,
        scenario=payload.scenario,
        triggered_by="api",
    )
    RUNNER.start(scan.id)
    return scan_summary(scan)


@router.get("", response_model=list[ScanSummary])
def list_scans(
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScanSummary]:
    scans = db.scalars(
        select(Scan)
        .join(Site)
        .where(Site.owner_id == user.id)
        .order_by(Scan.created_at.desc())
        .limit(limit)
    ).all()
    return [scan_summary(scan) for scan in scans]


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanOut:
    scan = _owned_scan(db, scan_id, user)
    return scan_out(scan)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    scan = _owned_scan(db, scan_id, user)
    RUNNER.cancel(scan_id)
    db.delete(scan)
    db.commit()


@router.get("/{scan_id}/report")
async def export_report(
    scan_id: str,
    format: str = Query(default="json", pattern="^(json|html|pdf)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scan = _owned_scan(db, scan_id, user)
    data = scan_out(scan)

    if format == "json":
        return JSONResponse(data.model_dump(mode="json"))

    content = render_report_html(data)
    if format == "html":
        return HTMLResponse(content)

    try:
        pdf = await html_to_pdf(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Génération PDF indisponible : {exc}") from exc

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapport_{scan_id}.pdf"'},
    )


@ws_router.websocket("/ws/scans/{scan_id}")
async def ws_scan(
    websocket: WebSocket,
    scan_id: str,
    token: str | None = Query(default=None),
) -> None:
    await websocket.accept()

    db = SessionLocal()
    try:
        try:
            user = user_from_token(token, db)
        except HTTPException as exc:
            await websocket.send_text(json.dumps({"type": "error", "message": exc.detail}))
            await websocket.close(code=4401)
            return

        scan = db.get(Scan, scan_id)
        if scan is None or scan.site is None or scan.site.owner_id != user.id:
            await websocket.send_text(json.dumps({"type": "error", "message": "Accès refusé."}))
            await websocket.close(code=4403)
            return

        for event in HUB.snapshot(scan_id):
            await websocket.send_text(json.dumps(event, default=str))

        if scan.status in ("completed", "failed"):
            await websocket.send_text(
                json.dumps({"type": "scan_done", "status": scan.status, "replay": True})
            )
            await websocket.close()
            return
    finally:
        db.close()

    queue = HUB.subscribe(scan_id)

    async def watch_disconnect() -> None:
        try:
            while True:
                await websocket.receive_text()
        except Exception:  # noqa: BLE001
            return

    watcher = asyncio.create_task(watch_disconnect())
    try:
        while True:
            getter = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait(
                {getter, watcher}, return_when=asyncio.FIRST_COMPLETED
            )
            if watcher in done:
                getter.cancel()
                break

            event = getter.result()
            await websocket.send_text(json.dumps(event, default=str))
            if event.get("type") == "scan_done":
                await websocket.close()
                break
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        watcher.cancel()
        HUB.unsubscribe(scan_id, queue)
