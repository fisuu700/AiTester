"""Agent d'accessibilité : axe-core injecté + contrôles manuels de secours."""

from __future__ import annotations

from pathlib import Path

from app.agents.base import AgentContext, AgentFinding, AgentReport, BaseAgent
from app.agents.browser import browser_page

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
AXE_LOCAL = Path(__file__).parent / "vendor" / "axe.min.js"

AXE_RUN = """
async () => {
  const result = await axe.run(document, {
    resultTypes: ['violations'],
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] }
  });
  return result.violations.map(v => ({
    id: v.id,
    impact: v.impact,
    help: v.help,
    description: v.description,
    nodes: v.nodes.slice(0, 5).map(n => (n.target || []).join(' '))
  }));
}
"""

FALLBACK_CHECK = """
() => {
  const issues = [];
  const images = Array.from(document.images || []);
  const noAlt = images.filter(img => !img.hasAttribute('alt'));
  if (noAlt.length) issues.push({id: 'image-alt', impact: 'serious', help: 'Images sans attribut alt', target: noAlt.slice(0,5).map(i => i.currentSrc || i.src)});

  const inputs = Array.from(document.querySelectorAll('input:not([type=hidden]), select, textarea'));
  const unlabeled = inputs.filter(el => {
    if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) return false;
    if (el.id && document.querySelector('label[for="' + el.id + '"]')) return false;
    return !el.closest('label');
  });
  if (unlabeled.length) issues.push({id: 'label', impact: 'serious', help: 'Champs de formulaire sans label', target: unlabeled.slice(0,5).map(el => el.name || el.id || el.tagName)});

  if (!document.documentElement.getAttribute('lang')) issues.push({id: 'html-has-lang', impact: 'serious', help: 'Langue du document non déclarée', target: ['<html>']});

  const h1 = document.querySelectorAll('h1');
  if (h1.length === 0) issues.push({id: 'page-has-heading-one', impact: 'moderate', help: 'Aucun titre h1', target: ['document']});
  if (h1.length > 1) issues.push({id: 'heading-order', impact: 'moderate', help: 'Plusieurs h1 sur la page', target: ['document']});

  const emptyLinks = Array.from(document.querySelectorAll('a')).filter(a => !(a.textContent || '').trim() && !a.getAttribute('aria-label') && !a.querySelector('img[alt]'));
  if (emptyLinks.length) issues.push({id: 'link-name', impact: 'serious', help: 'Liens sans texte accessible', target: emptyLinks.slice(0,5).map(a => a.href)});

  const emptyButtons = Array.from(document.querySelectorAll('button')).filter(b => !(b.textContent || '').trim() && !b.getAttribute('aria-label'));
  if (emptyButtons.length) issues.push({id: 'button-name', impact: 'serious', help: 'Boutons sans texte accessible', target: ['button']});

  return issues;
}
"""

IMPACT_MAP = {"critical": "critical", "serious": "high", "moderate": "medium", "minor": "low"}


class AccessibilityAgent(BaseAgent):
    name = "accessibility"
    label = "Accessibilité"

    async def run(self, ctx: AgentContext) -> AgentReport:
        findings: list[AgentFinding] = []
        engine = "axe-core"

        try:
            async with browser_page(ctx) as page:
                await page.goto(ctx.url, wait_until="domcontentloaded", timeout=ctx.timeout_ms)
                await page.wait_for_timeout(800)

                violations = None
                try:
                    if AXE_LOCAL.exists():
                        await page.add_script_tag(path=str(AXE_LOCAL))
                    else:
                        await page.add_script_tag(url=AXE_CDN, timeout=15000)
                    violations = await page.evaluate(AXE_RUN)
                except Exception:  # noqa: BLE001
                    ctx.log.warning("axe-core indisponible — contrôles manuels utilisés")
                    engine = "fallback"
                    issues = await page.evaluate(FALLBACK_CHECK)
                    violations = [
                        {
                            "id": issue.get("id"),
                            "impact": issue.get("impact"),
                            "help": issue.get("help"),
                            "description": issue.get("help"),
                            "nodes": issue.get("target") or [],
                        }
                        for issue in issues
                    ]
        except Exception as exc:  # noqa: BLE001
            ctx.log.error(f"Analyse d'accessibilité impossible : {type(exc).__name__}: {exc}")
            return AgentReport(
                agent=self.name,
                status="failed",
                findings=findings,
                error=f"{type(exc).__name__}: {exc}".strip(),
                score=None,
            )

        for violation in (violations or [])[:40]:
            severity = IMPACT_MAP.get(str(violation.get("impact")), "low")
            nodes = violation.get("nodes") or []
            findings.append(
                AgentFinding(
                    severity=severity,
                    category="wcag",
                    title=str(violation.get("help") or violation.get("id")),
                    description=str(violation.get("description") or ""),
                    url=ctx.url,
                    evidence=f"rule={violation.get('id')} · {len(nodes)} élément(s) · {', '.join(map(str, nodes[:3]))}",
                    remediation="Corriger le balisage selon la règle WCAG associée (axe-core / RGAA).",
                )
            )

        ctx.log.info(f"Accessibilité : {len(findings)} violation(s) ({engine})")
        return AgentReport(
            agent=self.name,
            findings=findings,
            metrics={"violations": len(findings), "engine": engine},
        )
