"""Registre des agents disponibles."""

from __future__ import annotations

from app.agents.accessibility import AccessibilityAgent
from app.agents.analyst import AnalystAgent
from app.agents.base import AgentContext, AgentFinding, AgentLogger, AgentReport, BaseAgent
from app.agents.functional import FunctionalAgent
from app.agents.performance import PerformanceAgent
from app.agents.reliability import ReliabilityAgent
from app.agents.security import SecurityAgent

AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "reliability": ReliabilityAgent,
    "security": SecurityAgent,
    "performance": PerformanceAgent,
    "accessibility": AccessibilityAgent,
    "functional": FunctionalAgent,
}

QUICK_AGENTS = ["reliability", "security"]
FULL_AGENTS = ["reliability", "security", "performance", "accessibility"]


def build_agents(mode: str, has_scenario: bool) -> list[BaseAgent]:
    names = list(FULL_AGENTS if mode == "full" else QUICK_AGENTS)
    if has_scenario and mode == "full":
        names.append("functional")
    return [AGENT_CLASSES[name]() for name in names]


__all__ = [
    "AGENT_CLASSES",
    "AgentContext",
    "AgentFinding",
    "AgentLogger",
    "AgentReport",
    "AnalystAgent",
    "BaseAgent",
    "build_agents",
]
