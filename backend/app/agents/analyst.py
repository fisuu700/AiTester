"""Agent analyste : synthèse globale et priorités de remédiation.

Appelle le LLM local (Ollama) si disponible, sinon produit une synthèse
déterministe à partir des findings (le LLM n'est jamais bloquant).
"""

from __future__ import annotations

import asyncio
import json

from app.agents.base import AgentContext, AgentFinding
from app.config import settings
from app.scoring import SEVERITY_ORDER, grade

AGENT_LABELS = {
    "reliability": "fiabilité",
    "security": "sécurité",
    "performance": "performance",
    "accessibility": "accessibilité",
    "functional": "fonctionnel",
}

ANALYST_PROMPT = """\
Tu es un analyste qualité et sécurité web. On te donne les résultats d'un scan
automatisé d'un site (fiabilité, sécurité, performance, accessibilité).

Réponds UNIQUEMENT avec du JSON valide, sans texte autour :
{"summary": "<synthèse en 3 phrases maximum>", "priorities": ["<action 1>", "<action 2>", "<action 3>"]}

Règles :
- Factuel, technique, pas de généralités.
- Priorise les problèmes critiques et élevés.
- Français, ton professionnel.
"""


class AnalystAgent:
    name = "analyst"

    async def summarize(
        self,
        ctx: AgentContext,
        findings: list[AgentFinding],
        scores: dict[str, float | None],
        global_score: float | None,
    ) -> str:
        fallback = self._deterministic(findings, scores, global_score)
        try:
            text = await asyncio.wait_for(
                self._llm_summary(ctx, findings, scores, global_score),
                timeout=min(settings.ollama_timeout, 90),
            )
            return text or fallback
        except Exception:  # noqa: BLE001
            ctx.log.info("Synthèse IA indisponible — résumé déterministe utilisé")
            return fallback

    # ------------------------------------------------------------------
    async def _llm_summary(
        self,
        ctx: AgentContext,
        findings: list[AgentFinding],
        scores: dict[str, float | None],
        global_score: float | None,
    ) -> str:
        import ollama

        payload = {
            "url": ctx.url,
            "global_score": global_score,
            "scores": scores,
            "findings": [
                {"severity": f.severity, "title": f.title, "agent": f.category}
                for f in findings[:60]
            ],
        }
        client = ollama.AsyncClient(host=settings.ollama_base_url)
        response = await client.chat(
            model=settings.model_analyst,
            messages=[
                {"role": "system", "content": ANALYST_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            format="json",
            options={"temperature": 0.2, "num_ctx": 8192},
            keep_alive="5m",
        )
        raw = response.message.content or ""
        data = json.loads(raw)
        summary = str(data.get("summary") or "").strip()
        priorities = [str(p) for p in (data.get("priorities") or [])][:3]
        if not summary:
            return ""
        if priorities:
            summary += "\n\nPriorités : " + " · ".join(priorities)
        return summary

    # ------------------------------------------------------------------
    @staticmethod
    def _deterministic(
        findings: list[AgentFinding],
        scores: dict[str, float | None],
        global_score: float | None,
    ) -> str:
        counts = {severity: 0 for severity in SEVERITY_ORDER}
        for finding in findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1

        parts: list[str] = []
        if global_score is not None:
            parts.append(f"Score global {global_score}/100 (note {grade(global_score)}).")
        else:
            parts.append("Score global indisponible.")

        present = [
            f"{AGENT_LABELS.get(name, name)} {value}/100"
            for name, value in scores.items()
            if value is not None
        ]
        if present:
            parts.append("Détail : " + ", ".join(present) + ".")

        total = len(findings)
        if total == 0:
            parts.append("Aucun problème détecté sur les contrôles exécutés.")
            return " ".join(parts)

        parts.append(
            f"{total} problème(s) : {counts['critical']} critique(s), "
            f"{counts['high']} élevé(s), {counts['medium']} moyen(s), {counts['low']} faible(s)."
        )

        top = [f for f in findings if f.severity in ("critical", "high")][:3]
        if top:
            parts.append("À traiter en priorité : " + "; ".join(f.title for f in top) + ".")
        return " ".join(parts)
