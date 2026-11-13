"""Agent de performance : métriques Web Vitals mesurées dans un vrai navigateur."""

from __future__ import annotations

from app.agents.base import AgentContext, AgentFinding, AgentReport, BaseAgent
from app.agents.browser import browser_page

INIT_SCRIPT = """
window.__perf = { lcp: 0, cls: 0 };
try {
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      window.__perf.lcp = entry.startTime;
    }
  }).observe({ type: 'largest-contentful-paint', buffered: true });
} catch (e) {}
try {
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__perf.cls += entry.value;
    }
  }).observe({ type: 'layout-shift', buffered: true });
} catch (e) {}
"""

COLLECT_SCRIPT = """
() => {
  const nav = performance.getEntriesByType('navigation')[0] || {};
  const resources = performance.getEntriesByType('resource') || [];
  let transfer = 0;
  for (const r of resources) { transfer += r.transferSize || 0; }
  const perf = window.__perf || {};
  return {
    ttfb: Math.round(nav.responseStart || 0),
    dom_content_loaded: Math.round(nav.domContentLoadedEventEnd || 0),
    load: Math.round(nav.loadEventEnd || 0),
    lcp: Math.round(perf.lcp || 0),
    cls: Math.round((perf.cls || 0) * 1000) / 1000,
    requests: resources.length,
    transfer_bytes: transfer,
    blocking_scripts: document.querySelectorAll('script[src]:not([async]):not([defer])').length,
    images: document.images.length,
    dom_nodes: document.getElementsByTagName('*').length,
  };
}
"""


class PerformanceAgent(BaseAgent):
    name = "performance"
    label = "Performance"

    async def run(self, ctx: AgentContext) -> AgentReport:
        findings: list[AgentFinding] = []
        metrics: dict = {}

        try:
            async with browser_page(ctx) as page:
                await page.add_init_script(INIT_SCRIPT)
                await page.goto(ctx.url, wait_until="load", timeout=ctx.timeout_ms)
                await page.wait_for_timeout(1200)
                metrics = await page.evaluate(COLLECT_SCRIPT)
        except Exception as exc:  # noqa: BLE001
            ctx.log.error(f"Mesure de performance impossible : {type(exc).__name__}: {exc}")
            return AgentReport(
                agent=self.name,
                status="failed",
                findings=findings,
                error=f"{type(exc).__name__}: {exc}".strip(),
                score=None,
            )

        lcp = metrics.get("lcp", 0)
        cls = metrics.get("cls", 0)
        ttfb = metrics.get("ttfb", 0)
        transfer_mb = metrics.get("transfer_bytes", 0) / (1024 * 1024)
        requests = metrics.get("requests", 0)
        blocking = metrics.get("blocking_scripts", 0)

        if lcp > 4000:
            findings.append(self._finding("high", "web-vitals", "LCP très lent", f"LCP = {lcp} ms (seuil 2500 ms).", f"lcp_ms={lcp}"))
        elif lcp > 2500:
            findings.append(self._finding("medium", "web-vitals", "LCP lent", f"LCP = {lcp} ms (seuil recommandé 2500 ms).", f"lcp_ms={lcp}"))

        if cls > 0.25:
            findings.append(self._finding("high", "web-vitals", "CLS dégradé", f"CLS = {cls} (seuil 0.1). Les éléments sautent pendant le chargement.", f"cls={cls}"))
        elif cls > 0.1:
            findings.append(self._finding("medium", "web-vitals", "CLS à surveiller", f"CLS = {cls} (seuil recommandé 0.1).", f"cls={cls}"))

        if ttfb > 1200:
            findings.append(self._finding("medium", "serveur", "TTFB élevé", f"Premier octet reçu après {ttfb} ms.", f"ttfb_ms={ttfb}"))
        elif ttfb > 800:
            findings.append(self._finding("low", "serveur", "TTFB à optimiser", f"TTFB = {ttfb} ms (seuil 800 ms).", f"ttfb_ms={ttfb}"))

        if transfer_mb > 5:
            findings.append(self._finding("high", "poids", "Page très lourde", f"{transfer_mb:.1f} Mo transférés.", f"transfer_mb={transfer_mb:.2f}"))
        elif transfer_mb > 3:
            findings.append(self._finding("medium", "poids", "Page lourde", f"{transfer_mb:.1f} Mo transférés.", f"transfer_mb={transfer_mb:.2f}"))

        if requests > 150:
            findings.append(self._finding("medium", "requêtes", "Trop de requêtes réseau", f"{requests} requêtes pour une seule page.", f"requests={requests}"))
        elif requests > 100:
            findings.append(self._finding("low", "requêtes", "Nombre de requêtes élevé", f"{requests} requêtes.", f"requests={requests}"))

        if blocking > 5:
            findings.append(self._finding("medium", "javascript", "Scripts bloquants", f"{blocking} scripts synchrones dans le <head>.", f"blocking_scripts={blocking}"))

        ctx.log.info(
            f"Performance : LCP {lcp} ms · CLS {cls} · TTFB {ttfb} ms · {requests} requêtes"
        )
        return AgentReport(agent=self.name, findings=findings, metrics=metrics)

    @staticmethod
    def _finding(severity: str, category: str, title: str, description: str, evidence: str) -> AgentFinding:
        return AgentFinding(
            severity=severity,
            category=category,
            title=title,
            description=description,
            evidence=evidence,
            remediation="Optimiser les ressources critiques, activer la compression et le cache navigateur.",
        )
