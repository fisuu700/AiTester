"""Agent fonctionnel : réutilise l'orchestrateur tri-couche (UI · API · DB) existant.

Ne s'exécute que si un scénario en langage naturel est fourni et que le mode
est `full`. Nécessite Ollama ; en cas d'indisponibilité, l'agent est marqué
`failed` sans bloquer le reste du scan.
"""

from __future__ import annotations

from app.agents.base import AgentContext, AgentFinding, AgentReport, BaseAgent

SEVERITY_MAP = {"info": "info", "warning": "medium", "error": "high"}


class FunctionalAgent(BaseAgent):
    name = "functional"
    label = "Fonctionnel"

    async def run(self, ctx: AgentContext) -> AgentReport:
        if not ctx.scenario or not ctx.scenario.strip():
            return AgentReport(
                agent=self.name,
                status="skipped",
                findings=[],
                score=None,
                metrics={"reason": "aucun scénario fourni"},
            )

        from app.orchestrator import Orchestrator
        from app.schemas import RunRequest

        ctx.log.info(f"Scénario fonctionnel : {ctx.scenario[:120]}")
        try:
            orchestrator = Orchestrator()
            report = await orchestrator.run(
                RunRequest(
                    target_url=ctx.url,
                    scenario=ctx.scenario,
                    max_steps=12,
                    headless=True,
                )
            )
        except Exception as exc:  # noqa: BLE001
            ctx.log.error(f"Agent fonctionnel en échec : {exc}")
            return AgentReport(agent=self.name, status="failed", error=str(exc), score=None)

        findings: list[AgentFinding] = []
        for anomaly in report.anomalies:
            findings.append(
                AgentFinding(
                    severity=SEVERITY_MAP.get(str(anomaly.severity.value), "medium"),
                    category=f"e2e-{anomaly.layer.value}",
                    title=f"Anomalie {anomaly.layer.value.upper()}",
                    description=anomaly.message,
                    url=ctx.url,
                    evidence=str(anomaly.details or ""),
                    remediation="Corriger l'incohérence entre l'interface, l'API et la base de données.",
                )
            )

        if report.root_cause:
            findings.append(
                AgentFinding(
                    severity="info",
                    category="analyse",
                    title="Cause racine identifiée",
                    description=report.root_cause,
                    url=ctx.url,
                    remediation="Traiter la cause racine avant de relancer le scénario.",
                )
            )

        ctx.log.info(
            f"Fonctionnel : {len(report.steps)} étape(s), {len(report.anomalies)} anomalie(s)"
        )
        return AgentReport(
            agent=self.name,
            findings=findings,
            metrics={"steps": len(report.steps), "success": report.success},
        )
