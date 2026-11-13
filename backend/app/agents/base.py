"""Contrat commun à tous les agents de scan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.config import settings


@dataclass
class AgentFinding:
    severity: str  # critical | high | medium | low | info
    category: str
    title: str
    description: str = ""
    url: str = ""
    evidence: str = ""
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }


@dataclass
class AgentReport:
    agent: str
    status: str = "completed"  # completed | skipped | failed
    findings: list[AgentFinding] = field(default_factory=list)
    score: float | None = 100.0
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class AgentLogger:
    """Petit adaptateur qui remonte les logs de l'agent vers le hub de scan."""

    def __init__(self, emit: Callable[[str, str, dict], None] | None = None, agent: str = "agent") -> None:
        self._emit = emit
        self.agent = agent

    def _send(self, level: str, message: str, data: dict | None = None) -> None:
        if self._emit:
            try:
                self._emit(level, message, {"agent": self.agent, **(data or {})})
            except Exception:  # noqa: BLE001
                pass

    def info(self, message: str, data: dict | None = None) -> None:
        self._send("info", message, data)

    def warning(self, message: str, data: dict | None = None) -> None:
        self._send("warning", message, data)

    def error(self, message: str, data: dict | None = None) -> None:
        self._send("error", message, data)


@dataclass
class AgentContext:
    url: str
    mode: str = "full"
    scenario: str | None = None
    log: AgentLogger = field(default_factory=lambda: AgentLogger())
    max_pages: int = field(default_factory=lambda: settings.max_pages_per_scan)
    max_links: int = field(default_factory=lambda: settings.max_links_checked)
    timeout_ms: int = field(default_factory=lambda: settings.browser_timeout_ms)
    request_timeout: int = field(default_factory=lambda: settings.request_timeout_seconds)
    user_agent: str = field(default_factory=lambda: settings.user_agent)


class BaseAgent:
    name: str = "base"
    label: str = "Base"

    async def run(self, ctx: AgentContext) -> AgentReport:  # pragma: no cover - interface
        raise NotImplementedError
