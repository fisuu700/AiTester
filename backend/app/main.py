"""Point d'entrée FastAPI : plateforme de scan + agent E2E historique.

Plateforme :
- /api/auth/*        → comptes, JWT, clé API
- /api/sites/*       → CRUD sites, lancement de scans, planification
- /api/scans/*       → résultats, export JSON/HTML/PDF
- /ws/scans/{id}     → progression temps réel

Agent historique (compatibilité PFE) :
- POST /api/run      → lance un scénario, retourne le rapport
- WS   /ws/run       → logs en direct
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.orchestrator import EventBus, Orchestrator
from app.routers import auth as auth_router
from app.routers import scans as scans_router
from app.routers import sites as sites_router
from app.scheduler import start_scheduler, stop_scheduler
from app.schemas import RunRequest


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    os.makedirs(settings.reports_dir, exist_ok=True)
    os.makedirs(settings.screenshots_dir, exist_ok=True)
    try:
        start_scheduler()
    except Exception:  # noqa: BLE001
        pass
    yield
    try:
        stop_scheduler()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.reports_dir, exist_ok=True)
os.makedirs(settings.screenshots_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=settings.reports_dir), name="reports")

app.include_router(auth_router.router)
app.include_router(sites_router.router)
app.include_router(scans_router.router)
app.include_router(scans_router.ws_router)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": settings.app_version})


# ---------------------------------------------------------------------------
# Agent E2E historique
# ---------------------------------------------------------------------------


@app.post("/api/run")
async def run_scenario(request: RunRequest) -> JSONResponse:
    """Exécute un scénario de bout en bout et retourne le rapport unifié."""
    orchestrator = Orchestrator()
    report = await orchestrator.run(request)
    return JSONResponse(
        content={
            "report": report.model_dump(mode="json"),
            "events": [e.model_dump(mode="json") for e in orchestrator.event_bus.queue],
        }
    )


@app.websocket("/ws/run")
async def ws_run(websocket: WebSocket) -> None:
    """Reçoit le scénario en JSON et streame les logs/événements en direct."""
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        payload = json.loads(raw)
        request = RunRequest.model_validate(payload)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await websocket.send_text(json.dumps({"type": "error", "message": f"Requête invalide : {exc}"}))
        await websocket.close()
        return

    orchestrator = Orchestrator()
    event_bus: EventBus = orchestrator.event_bus

    async def run_and_send() -> None:
        report = await orchestrator.run(request)
        await websocket.send_text(
            json.dumps({"type": "report", "report": report.model_dump(mode="json")}, default=str)
        )

    runner = asyncio.create_task(run_and_send())
    sent = 0
    try:
        while not runner.done():
            await asyncio.sleep(0.2)
            while sent < len(event_bus.queue):
                event = event_bus.queue[sent]
                await websocket.send_text(
                    json.dumps({"type": "log", "event": event.model_dump(mode="json")}, default=str)
                )
                sent += 1
        while sent < len(event_bus.queue):
            event = event_bus.queue[sent]
            await websocket.send_text(
                json.dumps({"type": "log", "event": event.model_dump(mode="json")}, default=str)
            )
            sent += 1
        await runner
    except WebSocketDisconnect:
        runner.cancel()
    except Exception as exc:  # noqa: BLE001
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:  # noqa: BLE001
            pass


@app.get("/api/reports")
async def list_reports() -> JSONResponse:
    from app.reporting.generator import ReportGenerator

    return JSONResponse(ReportGenerator(settings.reports_dir).list_reports())


@app.get("/api/reports/{run_id}")
async def get_report(run_id: str) -> JSONResponse:
    from app.reporting.generator import ReportGenerator

    report = ReportGenerator(settings.reports_dir).load(run_id)
    if not report:
        return JSONResponse({"error": "Rapport introuvable"}, status_code=404)
    return JSONResponse(report.model_dump(mode="json"))


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        # Windows : garantit une boucle compatible Playwright (sous-processus).
        loop="app.loop:proactor_loop_factory",
    )


if __name__ == "__main__":
    main()
