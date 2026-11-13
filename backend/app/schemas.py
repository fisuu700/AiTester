from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Layer(str, Enum):
    UI = "ui"
    API = "api"
    DB = "db"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DBConfig(BaseModel):
    url: str = Field(..., description="SQLAlchemy URL, ex: sqlite:///./demo_bank.db")


class RunRequest(BaseModel):
    target_url: str
    scenario: str = Field(..., min_length=3, description="Objectif en langage naturel")
    db: Optional[DBConfig] = None
    max_steps: int = 15
    headless: bool = True


class DBVerification(BaseModel):
    query: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    ok: bool = True
    error: Optional[str] = None


class APIObservation(BaseModel):
    url: str
    method: str = "GET"
    status: int = 0
    duration_ms: int = 0
    body: Optional[dict[str, Any]] = None


class UIAction(BaseModel):
    action: str
    selector: str
    value: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
    screenshot: Optional[str] = None
    dom_preview: str = ""


class Anomaly(BaseModel):
    layer: Layer
    severity: Severity = Severity.ERROR
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    index: int
    title: str
    ui: UIAction
    api: list[APIObservation] = Field(default_factory=list)
    db: Optional[DBVerification] = None
    anomalies: list[Anomaly] = Field(default_factory=list)
    root_cause: Optional[str] = None


class RunReport(BaseModel):
    run_id: str
    target_url: str
    scenario: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    success: bool = False
    steps: list[StepResult] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    root_cause: Optional[str] = None
    summary: str = ""


class LogEvent(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: str = "info"
    layer: Optional[Layer] = None
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Schémas de la plateforme (comptes, sites, scans, findings)
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime
    api_key: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SiteCreate(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    name: str = ""
    consent: bool = Field(..., description="L'utilisateur certifie être autorisé à tester ce site")


class SiteOut(BaseModel):
    id: int
    url: str
    name: str
    verified: bool
    created_at: datetime
    scans_count: int = 0
    last_scan: Optional["ScanSummary"] = None


class ScanCreate(BaseModel):
    mode: str = Field(default="full", pattern="^(quick|full)$")
    scenario: Optional[str] = None


class AgentResultOut(BaseModel):
    agent: str
    status: str
    score: float
    duration_ms: int
    error: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class FindingOut(BaseModel):
    id: int
    agent: str
    severity: str
    category: str
    title: str
    description: str
    url: str
    evidence: str
    remediation: str


class ScanSummary(BaseModel):
    id: str
    status: str
    mode: str
    global_score: Optional[float] = None
    findings_count: int = 0
    critical_count: int = 0
    created_at: datetime
    finished_at: Optional[datetime] = None


class ScanOut(BaseModel):
    id: str
    site_id: int
    site_url: str
    site_name: str
    status: str
    mode: str
    scenario: Optional[str] = None
    global_score: Optional[float] = None
    reliability_score: Optional[float] = None
    security_score: Optional[float] = None
    performance_score: Optional[float] = None
    accessibility_score: Optional[float] = None
    functional_score: Optional[float] = None
    summary: str = ""
    error: Optional[str] = None
    triggered_by: str = "manual"
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    agent_results: list[AgentResultOut] = Field(default_factory=list)
    findings: list[FindingOut] = Field(default_factory=list)


class HistoryPoint(BaseModel):
    scan_id: str
    created_at: datetime
    global_score: Optional[float] = None
    reliability_score: Optional[float] = None
    security_score: Optional[float] = None
    performance_score: Optional[float] = None
    accessibility_score: Optional[float] = None


class ScheduleCreate(BaseModel):
    cron: str = Field(default="0 3 * * *", max_length=64)
    mode: str = Field(default="full", pattern="^(quick|full)$")
    scenario: Optional[str] = None
    enabled: bool = True


class ScheduleOut(BaseModel):
    id: int
    site_id: int
    cron: str
    mode: str
    scenario: Optional[str] = None
    enabled: bool
    last_run: Optional[datetime] = None


class ApiScanRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    mode: str = Field(default="quick", pattern="^(quick|full)$")
    scenario: Optional[str] = None
    consent: bool = True


SiteOut.model_rebuild()
