"""Calcul des scores : pénalités par sévérité + score global pondéré."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.config import settings

SEVERITY_PENALTY = {
    "critical": 40.0,
    "high": 20.0,
    "medium": 8.0,
    "low": 3.0,
    "info": 0.0,
}

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def _get(finding: Any, key: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(key, default)
    return getattr(finding, key, default)


def score_from_findings(findings: Iterable[Any]) -> float:
    """Score 0-100 : 100 = aucun problème, dégressif selon les findings."""
    penalty = 0.0
    for finding in findings:
        severity = str(_get(finding, "severity", "info")).lower()
        penalty += SEVERITY_PENALTY.get(severity, 0.0)
    return round(max(0.0, 100.0 - penalty), 1)


def compute_global_score(per_agent: dict[str, float | None]) -> float | None:
    """Moyenne pondérée des scores d'agents disponibles (poids renormalisés)."""
    weights = settings.weights
    available = {name: score for name, score in per_agent.items() if score is not None}
    if not available:
        return None

    total_weight = sum(weights.get(name, 0.0) for name in available)
    if total_weight <= 0:
        return round(sum(available.values()) / len(available), 1)

    weighted = sum(score * weights.get(name, 0.0) for name, score in available.items())
    return round(weighted / total_weight, 1)


def severity_counts(findings: Iterable[Any]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        severity = str(_get(finding, "severity", "info")).lower()
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def grade(score: float | None) -> str:
    if score is None:
        return "?"
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "E"
