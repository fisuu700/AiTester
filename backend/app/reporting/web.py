"""Export du rapport de scan : HTML autonome et PDF (via Chromium)."""

from __future__ import annotations

import html as html_lib

from app.schemas import ScanOut
from app.scoring import grade

SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#0891b2",
    "info": "#64748b",
}

AGENT_LABELS = {
    "reliability": "Fiabilité",
    "security": "Sécurité",
    "performance": "Performance",
    "accessibility": "Accessibilité",
    "functional": "Fonctionnel",
}


def _score_block(label: str, value: float | None) -> str:
    shown = "—" if value is None else f"{value:.0f}"
    return (
        f'<div class="score"><span class="score-value">{shown}</span>'
        f'<span class="score-label">{html_lib.escape(label)}</span></div>'
    )


def render_report_html(scan: ScanOut) -> str:
    esc = html_lib.escape

    scores_html = "".join(
        _score_block(label, value)
        for label, value in [
            ("Global", scan.global_score),
            ("Fiabilité", scan.reliability_score),
            ("Sécurité", scan.security_score),
            ("Performance", scan.performance_score),
            ("Accessibilité", scan.accessibility_score),
        ]
    )

    findings_rows: list[str] = []
    for finding in scan.findings:
        color = SEVERITY_COLORS.get(finding.severity, "#64748b")
        findings_rows.append(
            "<tr>"
            f'<td><span class="badge" style="background:{color}">{esc(finding.severity.upper())}</span></td>'
            f"<td>{esc(AGENT_LABELS.get(finding.agent, finding.agent))}</td>"
            f"<td><strong>{esc(finding.title)}</strong>"
            + (f"<br><span class='muted'>{esc(finding.description)}</span>" if finding.description else "")
            + (f"<br><code>{esc(finding.evidence)}</code>" if finding.evidence else "")
            + "</td>"
            f"<td>{esc(finding.url)}</td>"
            f"<td class='muted'>{esc(finding.remediation)}</td>"
            "</tr>"
        )

    agents_rows = "".join(
        "<tr>"
        f"<td>{esc(AGENT_LABELS.get(result.agent, result.agent))}</td>"
        f"<td>{esc(result.status)}</td>"
        f"<td>{result.score:.0f}</td>"
        f"<td>{result.duration_ms / 1000:.1f}s</td>"
        f"<td class='muted'>{esc(result.error or '')}</td>"
        "</tr>"
        for result in scan.agent_results
    )

    findings_table = (
        "<table><thead><tr><th>Sévérité</th><th>Agent</th><th>Problème</th>"
        "<th>URL</th><th>Remédiation</th></tr></thead><tbody>"
        + ("".join(findings_rows) or "<tr><td colspan='5'>Aucun problème détecté.</td></tr>")
        + "</tbody></table>"
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Rapport de scan — {esc(scan.site_url)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: #0f172a;
         margin: 0; padding: 32px; background: #fff; font-size: 13px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 28px 0 8px; text-transform: uppercase;
        letter-spacing: .08em; color: #475569; }}
  .muted {{ color: #64748b; }}
  .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 16px; }}
  .scores {{ display: flex; gap: 12px; margin-top: 18px; flex-wrap: wrap; }}
  .score {{ flex: 1; min-width: 110px; border: 1px solid #e2e8f0; border-radius: 10px;
            padding: 12px; text-align: center; }}
  .score-value {{ display: block; font-size: 26px; font-weight: 700; }}
  .score-label {{ display: block; font-size: 11px; color: #64748b; text-transform: uppercase; }}
  .grade {{ font-size: 44px; font-weight: 800; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th {{ text-align: left; font-size: 11px; text-transform: uppercase; color: #475569;
        border-bottom: 1px solid #cbd5e1; padding: 8px 6px; }}
  td {{ border-bottom: 1px solid #e2e8f0; padding: 8px 6px; vertical-align: top; }}
  .badge {{ color: #fff; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: 700; }}
  code {{ font-size: 11px; color: #334155; word-break: break-all; }}
  .summary {{ background: #f1f5f9; border-left: 4px solid #0ea5e9; padding: 12px 16px;
              border-radius: 6px; white-space: pre-wrap; }}
</style>
</head>
<body>
  <div class="header">
    <h1>Rapport de scan — {esc(scan.site_name)}</h1>
    <p class="muted">
      {esc(scan.site_url)} · scan <code>{esc(scan.id)}</code> · mode {esc(scan.mode)}
    </p>
    <div class="scores">
      {scores_html}
      <div class="score"><span class="grade">{grade(scan.global_score)}</span>
        <span class="score-label">Note</span></div>
    </div>
  </div>

  <h2>Synthèse</h2>
  <div class="summary">{esc(scan.summary or "Aucune synthèse disponible.")}</div>

  <h2>Agents</h2>
  <table><thead><tr><th>Agent</th><th>Statut</th><th>Score</th><th>Durée</th>
  <th>Erreur</th></tr></thead><tbody>{agents_rows}</tbody></table>

  <h2>Problèmes détectés ({len(scan.findings)})</h2>
  {findings_table}

  <p class="muted" style="margin-top:24px;font-size:11px">
    Scan passif automatisé — rapport généré par AI E2E Testing Agent.
  </p>
</body>
</html>"""


async def html_to_pdf(content: str) -> bytes:
    """Rend le rapport HTML en PDF via Chromium headless."""
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    try:
        page = await browser.new_page()
        await page.set_content(content, wait_until="load")
        return await page.pdf(format="A4", print_background=True, margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
    finally:
        await browser.close()
        await playwright.stop()
