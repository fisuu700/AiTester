"""Orchestrateur de scan : exécute les agents en parallèle et persiste les résultats.

Diffusion temps réel via un hub en mémoire (WebSocket).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.agents import AgentLogger, AgentReport, AnalystAgent, build_agents
from app.agents.base import AgentContext
from app.config import settings
from app.db import SessionLocal
from app.models import AgentResult, Finding, Scan, Site
from app.scoring import compute_global_score, score_from_findings


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScanHub:
    """Bus d'événements en mémoire, un canal par scan."""

    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def publish(self, scan_id: str, event: dict[str, Any]) -> None:
        event.setdefault("ts", _now().isoformat())
        self._events.setdefault(scan_id, []).append(event)
        # garde-fou mémoire
        if len(self._events[scan_id]) > 2000:
            del self._events[scan_id][:1000]
        for queue in list(self._subscribers.get(scan_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def snapshot(self, scan_id: str) -> list[dict[str, Any]]:
        return list(self._events.get(scan_id, []))

    def subscribe(self, scan_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.setdefault(scan_id, []).append(queue)
        return queue

    def unsubscribe(self, scan_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(scan_id, [])
        if queue in subscribers:
            subscribers.remove(queue)


HUB = ScanHub()


class ScanRunner:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_scans)

    def start(self, scan_id: str, loop: asyncio.AbstractEventLoop | None = None) -> None:
        if scan_id in self._tasks:
            return
        target_loop = loop or asyncio.get_running_loop()
        task = target_loop.create_task(self._run(scan_id))
        self._tasks[scan_id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(scan_id, None))

    def cancel(self, scan_id: str) -> bool:
        task = self._tasks.get(scan_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def _run(self, scan_id: str) -> None:
        async with self._semaphore:
            db = SessionLocal()
            try:
                await self._execute(db, scan_id)
            except asyncio.CancelledError:
                scan = db.get(Scan, scan_id)
                if scan:
                    scan.status = "failed"
                    scan.error = "Scan annulé."
                    scan.finished_at = _now()
                    db.commit()
                HUB.publish(scan_id, {"type": "scan_done", "status": "failed", "error": "annulé"})
                raise
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                scan = db.get(Scan, scan_id)
                if scan:
                    scan.status = "failed"
                    scan.error = str(exc)
                    scan.finished_at = _now()
                    db.commit()
                HUB.publish(scan_id, {"type": "scan_done", "status": "failed", "error": str(exc)})
            finally:
                db.close()

    # ------------------------------------------------------------------
    async def _execute(self, db, scan_id: str) -> None:
        scan = db.get(Scan, scan_id)
        if scan is None:
            HUB.publish(scan_id, {"type": "scan_done", "status": "failed", "error": "Scan introuvable"})
            return

        site = db.get(Site, scan.site_id)
        if site is None:
            scan.status = "failed"
            scan.error = "Site introuvable."
            db.commit()
            return

        scan.status = "running"
        scan.started_at = _now()
        db.commit()

        def emit(level: str, message: str, data: dict | None = None) -> None:
            HUB.publish(
                scan_id,
                {"type": "log", "level": level, "message": message, "data": data or {}},
            )

        HUB.publish(
            scan_id,
            {
                "type": "scan_status",
                "status": "running",
                "site_url": site.url,
                "mode": scan.mode,
            },
        )
        emit("info", f"Scan {scan_id} démarré sur {site.url} (mode {scan.mode})")

        agents = build_agents(scan.mode, bool(scan.scenario))
        results = await asyncio.gather(
            *(
                self._run_agent(scan_id, agent, site.url, scan.mode, scan.scenario, emit)
                for agent in agents
            )
        )

        per_agent: dict[str, float | None] = {}
        all_findings = []

        for agent, report, score, duration_ms in results:
            per_agent[agent.name] = score
            all_findings.extend(report.findings)
            db.add(
                AgentResult(
                    scan_id=scan_id,
                    agent=agent.name,
                    status=report.status,
                    score=score if score is not None else 0.0,
                    duration_ms=duration_ms,
                    error=report.error,
                    metrics=json.dumps(report.metrics, ensure_ascii=False, default=str),
                )
            )
            for finding in report.findings:
                db.add(
                    Finding(
                        scan_id=scan_id,
                        agent=agent.name,
                        severity=finding.severity,
                        category=finding.category,
                        title=finding.title,
                        description=finding.description,
                        url=finding.url,
                        evidence=finding.evidence,
                        remediation=finding.remediation,
                    )
                )
            HUB.publish(
                scan_id,
                {
                    "type": "agent_done",
                    "agent": agent.name,
                    "label": agent.label,
                    "status": report.status,
                    "score": score,
                    "findings": len(report.findings),
                    "duration_ms": duration_ms,
                },
            )

        global_score = compute_global_score(per_agent)
        scan.reliability_score = per_agent.get("reliability")
        scan.security_score = per_agent.get("security")
        scan.performance_score = per_agent.get("performance")
        scan.accessibility_score = per_agent.get("accessibility")
        scan.functional_score = per_agent.get("functional")
        scan.global_score = global_score

        analyst_ctx = AgentContext(
            url=site.url,
            mode=scan.mode,
            scenario=scan.scenario,
            log=AgentLogger(emit, "analyst"),
        )
        scan.summary = await AnalystAgent().summarize(analyst_ctx, all_findings, per_agent, global_score)

        any_success = any(report.status in ("completed", "skipped") for _, report, _, _ in results)
        scan.status = "completed" if any_success else "failed"
        if not any_success:
            scan.error = "Tous les agents ont échoué."
        scan.finished_at = _now()
        db.commit()

        emit("info", f"Scan terminé — score global {global_score}/100")
        HUB.publish(
            scan_id,
            {
                "type": "scan_done",
                "status": scan.status,
                "global_score": global_score,
                "scores": per_agent,
                "summary": scan.summary,
                "findings_total": len(all_findings),
            },
        )

    # ------------------------------------------------------------------
    async def _run_agent(
        self,
        scan_id: str,
        agent,
        url: str,
        mode: str,
        scenario: str | None,
        emit,
    ) -> tuple[Any, AgentReport, float | None, int]:
        HUB.publish(
            scan_id,
            {"type": "agent_start", "agent": agent.name, "label": agent.label},
        )
        started = time.perf_counter()
        ctx = AgentContext(
            url=url,
            mode=mode,
            scenario=scenario,
            log=AgentLogger(emit, agent.name),
        )
        try:
            report = await asyncio.wait_for(
                agent.run(ctx), timeout=settings.agent_timeout_seconds
            )
        except asyncio.TimeoutError:
            report = AgentReport(
                agent=agent.name,
                status="failed",
                error=f"Délai dépassé ({settings.agent_timeout_seconds}s)",
                score=None,
            )
        except Exception as exc:  # noqa: BLE001
            report = AgentReport(
                agent=agent.name,
                status="failed",
                error=f"{type(exc).__name__}: {exc}".strip(),
                score=None,
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        if report.status == "skipped":
            score: float | None = None
        elif report.status == "failed" and not report.findings:
            score = None
        else:
            score = report.score if report.score is not None else 100.0
            score = score_from_findings(report.findings) if report.findings else score
        return agent, report, score, duration_ms


RUNNER = ScanRunner()


def create_scan(db, site: Site, mode: str = "full", scenario: str | None = None, triggered_by: str = "manual") -> Scan:
    scan = Scan(
        site_id=site.id,
        mode=mode,
        scenario=scenario,
        triggered_by=triggered_by,
        status="queued",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def latest_scan(db, site_id: int) -> Scan | None:
    return db.scalar(
        select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc()).limit(1)
    )
