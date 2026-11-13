"""Multi-Model Router : route chaque sous-tâche vers le modèle le plus adapté.

- llama3.1:8b     → planificateur (objectif → étapes JSON)
- qwen2.5-coder:7b → exécutant (sélecteurs CSS + SQL)
- deepseek-r1:7b  → analyste (root cause analysis)

Les modèles sont appelés séquentiellement (jamais 2 simultanés) pour
respecter la contrainte de 16 Go de RAM.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import ollama
from pydantic import ValidationError

from app.config import settings
from app.schemas import StepResult

_REJECT_RE = re.compile(
    r"\b(select|insert|update|delete|drop|alter|truncate|create|replace)\b.*?\b("
    r"from|into|table|set|values|database|schema)\b",
    re.IGNORECASE,
)


class AIError(Exception):
    pass


class MultiModelRouter:
    """Délègue chaque sous-tâche au modèle le plus adapté."""

    def __init__(self, logger) -> None:
        self.client = ollama.AsyncClient(host=settings.ollama_base_url)
        self.log = logger

    async def _chat_json(self, model: str, system: str, user: str) -> dict[str, Any]:
        options = {"temperature": 0.1, "num_ctx": 8192}
        self.log.info(
            f"Appel IA [{model}]",
            layer=None,
            data={"model": model, "user_chars": len(user)},
        )
        try:
            response = await self.client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                format="json",
                options=options,
                keep_alive="5m",
            )
        except Exception as exc:  # noqa: BLE001
            raise AIError(f"Échec de l'appel Ollama ({model}) : {exc}") from exc

        raw = response.message.content or ""
        return self._parse_json(raw, model)

    @staticmethod
    def _extract_json(raw: str) -> Optional[str]:
        raw = raw.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        return match.group(0) if match else None

    def _parse_json(self, raw: str, model: str) -> dict[str, Any]:
        text = self._extract_json(raw)
        if not text:
            raise AIError(f"Réponse non-JSON du modèle {model} : {raw[:200]}")
        for attempt in (text, re.sub(r",\s*([}\]])", r"\1", text)):
            try:
                parsed = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise AIError(f"JSON invalide du modèle {model} : {text[:200]}")

    # ------------------------------------------------------------------
    # Rôle 1 : planificateur
    # ------------------------------------------------------------------
    async def plan_scenario(self, scenario: str, target_url: str, max_steps: int) -> list[dict[str, Any]]:
        from app.ai.prompts import PLANNER_SYSTEM_PROMPT

        system = PLANNER_SYSTEM_PROMPT.format(max_steps=max_steps)
        user = f"URL cible : {target_url}\nObjectif : {scenario}"
        data = await self._chat_json(settings.model_planner, system, user)
        steps = data.get("steps")
        if not isinstance(steps, list) or not steps:
            raise AIError("Le planificateur n'a retourné aucune étape.")
        normalized: list[dict[str, Any]] = []
        for i, step in enumerate(steps[:max_steps], start=1):
            normalized.append(
                {
                    "index": i,
                    "title": str(step.get("title") or f"Étape {i}"),
                    "instruction": str(step.get("instruction") or ""),
                }
            )
        return normalized

    # ------------------------------------------------------------------
    # Rôle 2 : exécutant (DOM → sélecteur CSS + SQL)
    # ------------------------------------------------------------------
    async def execute_step(
        self, instruction: str, dom_html: str, schema_hint: Optional[str] = None
    ) -> dict[str, Any]:
        from app.ai.prompts import EXECUTOR_SYSTEM_PROMPT

        user = (
            f"Instruction : {instruction}\n\n"
            f"Schéma DB (si disponible) : {schema_hint or 'inconnu'}\n\n"
            f"DOM HTML nettoyé de la page courante :\n{dom_html}"
        )
        data = await self._chat_json(settings.model_executor, EXECUTOR_SYSTEM_PROMPT, user)
        action = str(data.get("action") or "wait").lower()
        selector = str(data.get("selector") or "")
        value = data.get("value")
        db_check = data.get("db_check")
        return {
            "action": action,
            "selector": selector,
            "value": None if value in (None, "null", "") else str(value),
            "db_check": str(db_check) if db_check else None,
        }

    # ------------------------------------------------------------------
    # Rôle 2bis : requête SQL de contrôle d'intégrité
    # ------------------------------------------------------------------
    async def generate_db_check(self, instruction: str, schema_hint: str) -> str:
        from app.ai.prompts import DB_CHECK_SYSTEM_PROMPT

        user = f"Étape exécutée : {instruction}\n\nSchéma DB :\n{schema_hint}"
        data = await self._chat_json(settings.model_executor, DB_CHECK_SYSTEM_PROMPT, user)
        return str(data.get("query") or "")

    # ------------------------------------------------------------------
    # Rôle 3 : analyste / débogueur
    # ------------------------------------------------------------------
    async def diagnose(self, report: StepResult, scenario: str) -> dict[str, Any]:
        from app.ai.prompts import ANALYST_SYSTEM_PROMPT

        observations = {
            "ui": report.ui.model_dump(exclude={"dom_preview"}),
            "api": [o.model_dump() for o in report.api],
            "db": report.db.model_dump() if report.db else None,
            "anomalies": [a.model_dump() for a in report.anomalies],
        }
        user = (
            f"Scénario : {scenario}\n"
            f"Étape en échec : [{report.index}] {report.title}\n"
            f"Observations : {json.dumps(observations, ensure_ascii=False, default=str)}"
        )
        data = await self._chat_json(settings.model_analyst, ANALYST_SYSTEM_PROMPT, user)
        severity = str(data.get("severity") or "error").lower()
        if severity not in ("info", "warning", "error"):
            severity = "error"
        return {
            "root_cause": str(data.get("root_cause") or ""),
            "severity": severity,
            "summary": str(data.get("summary") or ""),
        }

    # ------------------------------------------------------------------
    # Garde-fou SQL (lecture seule uniquement)
    # ------------------------------------------------------------------
    @staticmethod
    def validate_readonly_sql(query: str) -> tuple[bool, str]:
        stripped = query.strip().rstrip(";").strip()
        if not re.match(r"(?is)^select\b", stripped):
            return False, "Seules les requêtes SELECT sont autorisées."
        # Pas de commentaire SQL ni de SELECT ... INTO
        if "--" in stripped or "/*" in stripped:
            return False, "Les commentaires SQL sont interdits."
        if re.search(r"(?is)\binto\b", stripped):
            return False, "SELECT ... INTO est interdit."
        if _REJECT_RE.search(stripped) and not re.match(r"(?is)^select\b", stripped):
            return False, "Requête non-SELECT détectée."
        # Sous-requêtes : aucun mot-clé de mutation
        if re.search(r"(?is)\b(insert|update|delete|drop|alter|truncate|create)\b", stripped):
            return False, "Mot-clé de mutation détecté."
        return True, ""

    # ------------------------------------------------------------------
    # Validation JSON sur ValidationError de pydantic (usage explicite)
    # ------------------------------------------------------------------
    @staticmethod
    def coerce_validation_error(exc: ValidationError) -> str:
        return "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors())
