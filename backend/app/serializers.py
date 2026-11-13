"""Sérialisation des modèles ORM vers les schémas Pydantic."""

from __future__ import annotations

import json

from app.models import Scan, Site
from app.schemas import AgentResultOut, FindingOut, ScanOut, ScanSummary, SiteOut


def scan_summary(scan: Scan) -> ScanSummary:
    findings = scan.findings or []
    return ScanSummary(
        id=scan.id,
        status=scan.status,
        mode=scan.mode,
        global_score=scan.global_score,
        findings_count=len(findings),
        critical_count=sum(1 for f in findings if f.severity == "critical"),
        created_at=scan.created_at,
        finished_at=scan.finished_at,
    )


def scan_out(scan: Scan) -> ScanOut:
    site = scan.site
    return ScanOut(
        id=scan.id,
        site_id=scan.site_id,
        site_url=site.url if site else "",
        site_name=(site.name or site.url) if site else "",
        status=scan.status,
        mode=scan.mode,
        scenario=scan.scenario,
        global_score=scan.global_score,
        reliability_score=scan.reliability_score,
        security_score=scan.security_score,
        performance_score=scan.performance_score,
        accessibility_score=scan.accessibility_score,
        functional_score=scan.functional_score,
        summary=scan.summary or "",
        error=scan.error,
        triggered_by=scan.triggered_by,
        created_at=scan.created_at,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
        agent_results=[
            AgentResultOut(
                agent=result.agent,
                status=result.status,
                score=result.score,
                duration_ms=result.duration_ms,
                error=result.error,
                metrics=_safe_json(result.metrics),
            )
            for result in sorted(scan.agent_results, key=lambda r: r.id)
        ],
        findings=[
            FindingOut(
                id=finding.id,
                agent=finding.agent,
                severity=finding.severity,
                category=finding.category,
                title=finding.title,
                description=finding.description,
                url=finding.url,
                evidence=finding.evidence,
                remediation=finding.remediation,
            )
            for finding in sorted(scan.findings, key=lambda f: f.id)
        ],
    )


def site_out(site: Site) -> SiteOut:
    scans = sorted(site.scans or [], key=lambda s: s.created_at, reverse=True)
    return SiteOut(
        id=site.id,
        url=site.url,
        name=site.name or site.url,
        verified=site.verified,
        created_at=site.created_at,
        scans_count=len(scans),
        last_scan=scan_summary(scans[0]) if scans else None,
    )


def _safe_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"value": value}
    except (json.JSONDecodeError, TypeError):
        return {}
