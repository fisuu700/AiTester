"""Boucle autonome d'exécution : synchronisation asynchrone entre le navigateur,
les appels IA et la base de données (validation tri-couche UI / API / DB).

Pipeline :
  1. llama3.1:8b      → plan du scénario (étapes JSON)
  2. qwen2.5-coder:7b → par étape : sélecteur CSS + action + SQL de contrôle
  3. Playwright       → exécution UI + capture d'écran
  4. API Monitor      → audit des échanges HTTP
  5. DB Validator     → requête SELECT d'intégrité
  6. deepseek-r1:7b   → si anomalie : root cause analysis
  7. Rapport unifié   → JSON + screenshots
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from app.ai.router import AIError, MultiModelRouter
from app.config import settings
from app.engines.api_monitor import APIMonitor
from app.engines.db_validator import DBValidator
from app.engines.ui_engine import UIEngine
from app.reporting.generator import ReportGenerator
from app.schemas import (
    Anomaly,
    Layer,
    LogEvent,
    RunReport,
    RunRequest,
    Severity,
    StepResult,
)


class EventBus:
    """Collecte les événements de log ; le backend les diffuse en WebSocket."""

    def __init__(self) -> None:
        self.queue: list[LogEvent] = []

    def info(self, message: str, data: dict | None = None) -> None:
        self._emit("info", message, data)

    def warning(self, message: str, data: dict | None = None) -> None:
        self._emit("warning", message, data)

    def error(self, message: str, data: dict | None = None) -> None:
        self._emit("error", message, data)

    def _emit(self, level: str, message: str, data: dict | None) -> None:
        self.queue.append(LogEvent(level=level, message=message, data=data or {}))


class Orchestrator:
    def __init__(self) -> None:
        self.event_bus = EventBus()
        self.log = self.event_bus
        self.router = MultiModelRouter(self.log)
        self.ui = UIEngine(self.log, screenshots_dir=settings.screenshots_dir)
        self.monitor = APIMonitor(self.log)
        self.db = DBValidator(self.log)
        self.reports = ReportGenerator(settings.reports_dir)

    async def run(self, request: RunRequest) -> RunReport:
        run_id = uuid.uuid4().hex[:12]
        report = RunReport(run_id=run_id, target_url=request.target_url, scenario=request.scenario)
        os.makedirs(settings.screenshots_dir, exist_ok=True)

        self.log.info(f"Run {run_id} démarré — cible : {request.target_url}")

        try:
            # 1. Planification (llama3.1:8b)
            steps = await self.router.plan_scenario(
                request.scenario, request.target_url, request.max_steps
            )
            self.log.info(f"Plan généré : {len(steps)} étapes", data={"steps": [s["title"] for s in steps]})

            # 2. Initialisation navigateur + interception réseau
            await self.ui.start(request.target_url, headless=request.headless)
            if self.ui.page:
                self.monitor.attach(self.ui.page)

            # 3. Connexion DB (optionnelle)
            schema_hint = ""
            if request.db and request.db.url:
                try:
                    self.db.connect(request.db.url)
                    schema_hint = self.db.get_schema_hint()
                    self.log.info(f"Schéma détecté : {schema_hint[:300]}")
                except Exception as exc:  # noqa: BLE001
                    self.log.warning(f"Connexion DB impossible : {exc}")

            # 4. Boucle d'exécution par étape
            for step in steps:
                step_result = await self._run_step(run_id, step, schema_hint)
                report.steps.append(step_result)
                report.anomalies.extend(step_result.anomalies)
                if step_result.root_cause:
                    report.root_cause = step_result.root_cause

            # 5. Diagnostique global si des anomalies ont été détectées
            if report.anomalies:
                report.success = False
                if not report.root_cause:
                    await self._diagnose_global(report)
            else:
                report.success = True
                report.summary = f"Scénario exécuté avec succès : {len(report.steps)} étapes, aucune anomalie UI/API/DB."

            self.log.info(f"Run {run_id} terminé — succès : {report.success}")
        except AIError as exc:
            report.success = False
            report.root_cause = f"Erreur IA : {exc}"
            self.log.error(f"Erreur IA : {exc}")
        except Exception as exc:  # noqa: BLE001
            report.success = False
            report.root_cause = f"Erreur orchestrateur : {exc}"
            self.log.error(f"Erreur orchestrateur : {exc}")
        finally:
            report.finished_at = datetime.now(timezone.utc)
            await self.ui.stop()
            self.db.close()

        path = self.reports.save(report)
        self.log.info(f"Rapport enregistré : {path}")
        return report

    async def _run_step(self, run_id: str, step: dict, schema_hint: str) -> StepResult:
        index = step["index"]
        title = step["title"]
        instruction = step["instruction"]
        result = StepResult(index=index, title=title, ui=None, root_cause=None)  # type: ignore[arg-type]
        self.log.info(f"[{index}/{len(step) and '' or ''}] {title} — {instruction}")

        # 4a. Exécutant technique (qwen2.5-coder) : DOM → sélecteur CSS + SQL
        dom = await self.ui.current_dom()
        try:
            plan = await self.router.execute_step(instruction, dom, schema_hint)
        except AIError as exc:
            anomaly = Anomaly(layer=Layer.UI, message=f"Exécutant IA en échec : {exc}")
            result.ui = await self.ui.run_action(run_id, index, "wait", None, None)
            result.anomalies.append(anomaly)
            return await self._diagnose_step(run_id, result)

        self.log.info(
            f"Action déduite : {plan['action']} {plan['selector']} {plan['value'] or ''}".rstrip()
        )

        # 4b. Exécution UI (Playwright)
        result.ui = await self.ui.run_action(run_id, index, plan["action"], plan["selector"], plan["value"])
        if not result.ui.ok:
            result.anomalies.append(Anomaly(layer=Layer.UI, message=result.ui.error or "Échec UI"))

        # 4c. Audit API (interception réseau)
        recent = self.monitor.snapshot_since(n=30)
        result.api = recent
        for message in self.monitor.check_observations(recent):
            result.anomalies.append(Anomaly(layer=Layer.API, message=message))

        # 4d. Contrôle d'intégrité DB (SELECT)
        if self.db.connected and plan["db_check"]:
            verification = await self.db.verify(plan["db_check"])
            result.db = verification
            if not verification.ok:
                result.anomalies.append(
                    Anomaly(layer=Layer.DB, message=f"DB check en échec : {verification.error}")
                )
            elif verification.row_count == 0:
                result.anomalies.append(
                    Anomaly(
                        layer=Layer.DB,
                        severity=Severity.WARNING,
                        message="DB check : 0 ligne retournée (donnée absente ?)",
                        details={"query": verification.query},
                    )
                )

        # 4e. Root cause analysis (deepseek-r1) si anomalie
        if result.anomalies:
            return await self._diagnose_step(run_id, result)
        return result

    async def _diagnose_step(self, run_id: str, result: StepResult) -> StepResult:
        try:
            diagnosis = await self.router.diagnose(result, scenario=result.title)
            result.root_cause = diagnosis["root_cause"]
        except AIError as exc:
            self.log.warning(f"Analyse root cause indisponible : {exc}")
        return result

    async def _diagnose_global(self, report: RunReport) -> None:
        last_failed = next((s for s in reversed(report.steps) if s.anomalies), None)
        if not last_failed:
            return
        try:
            diagnosis = await self.router.diagnose(last_failed, scenario=report.scenario)
            report.root_cause = diagnosis["root_cause"]
            report.summary = diagnosis["summary"]
        except AIError as exc:
            report.summary = f"Exécution terminée avec {len(report.anomalies)} anomalie(s). Analyse indisponible : {exc}"
