"""Agent de fiabilité : crawl du site, statuts HTTP, liens morts, timeouts."""

from __future__ import annotations

import time
from collections import deque
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.agents.base import AgentContext, AgentFinding, AgentReport, BaseAgent
from app.safety import cache_robots, get_cached_robots, is_path_allowed, parse_robots

SLOW_PAGE_MS = 3000
MIN_BODY_CHARS = 200


class ReliabilityAgent(BaseAgent):
    name = "reliability"
    label = "Fiabilité"

    async def run(self, ctx: AgentContext) -> AgentReport:
        findings: list[AgentFinding] = []
        pages_checked = 0
        links_checked = 0
        total_ms = 0.0
        origin = self._origin(ctx.url)

        headers = {"User-Agent": ctx.user_agent, "Accept": "text/html,application/xhtml+xml"}
        limits = httpx.Limits(max_connections=8, max_keepalive_connections=4)

        async with httpx.AsyncClient(
            verify=False,
            follow_redirects=True,
            timeout=ctx.request_timeout,
            headers=headers,
            limits=limits,
            trust_env=False,
        ) as client:
            await self._load_robots(client, origin, ctx)
            rules = get_cached_robots(origin)

            visited: set[str] = set()
            queue: deque[str] = deque([ctx.url])
            discovered: list[str] = []

            while queue and pages_checked < ctx.max_pages:
                url = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)

                path = urlparse(url).path or "/"
                if not is_path_allowed(path, rules):
                    ctx.log.info(f"robots.txt interdit {path} — ignoré")
                    continue

                started = time.perf_counter()
                try:
                    response = await client.get(url)
                except httpx.TimeoutException:
                    findings.append(
                        AgentFinding(
                            severity="high",
                            category="disponibilité",
                            title="Délai de réponse dépassé",
                            description=f"La page n'a pas répondu en {ctx.request_timeout}s.",
                            url=url,
                            evidence=f"timeout={ctx.request_timeout}s",
                            remediation="Vérifier le serveur, le DNS et les timeouts applicatifs.",
                        )
                    )
                    continue
                except httpx.HTTPError as exc:
                    findings.append(
                        AgentFinding(
                            severity="high",
                            category="disponibilité",
                            title="Page inaccessible",
                            description=str(exc),
                            url=url,
                            evidence=type(exc).__name__,
                            remediation="Vérifier la disponibilité du service et la configuration TLS.",
                        )
                    )
                    continue

                elapsed_ms = (time.perf_counter() - started) * 1000
                total_ms += elapsed_ms
                pages_checked += 1
                content_type = response.headers.get("content-type", "")

                if response.status_code >= 500:
                    findings.append(
                        AgentFinding(
                            severity="critical",
                            category="disponibilité",
                            title=f"Erreur serveur HTTP {response.status_code}",
                            description="Le serveur répond par une erreur interne.",
                            url=url,
                            evidence=f"status={response.status_code}",
                            remediation="Consulter les logs serveur et corriger l'exception applicative.",
                        )
                    )
                elif response.status_code >= 400:
                    findings.append(
                        AgentFinding(
                            severity="high",
                            category="disponibilité",
                            title=f"Erreur client HTTP {response.status_code}",
                            description="La ressource est introuvable ou refuse l'accès.",
                            url=url,
                            evidence=f"status={response.status_code}",
                            remediation="Vérifier la route, les permissions et les redirections.",
                        )
                    )

                if elapsed_ms > SLOW_PAGE_MS:
                    findings.append(
                        AgentFinding(
                            severity="medium",
                            category="performance",
                            title="Page lente",
                            description=f"Temps de réponse de {elapsed_ms:.0f} ms.",
                            url=url,
                            evidence=f"duration_ms={elapsed_ms:.0f}",
                            remediation="Ajouter un cache, optimiser les requêtes serveur ou un CDN.",
                        )
                    )

                if response.history and len(response.history) > 5:
                    findings.append(
                        AgentFinding(
                            severity="medium",
                            category="configuration",
                            title="Chaîne de redirections trop longue",
                            description=f"{len(response.history)} redirections avant la page finale.",
                            url=url,
                            evidence=" → ".join(str(r.status_code) for r in response.history),
                            remediation="Réduire les redirections (max 1 à 2).",
                        )
                    )

                if "html" not in content_type:
                    continue

                html = response.text or ""
                if len(html) < MIN_BODY_CHARS and url == ctx.url:
                    findings.append(
                        AgentFinding(
                            severity="high",
                            category="contenu",
                            title="Page d'accueil quasi vide",
                            description="Le HTML retourné est très court : page blanche ou erreur masquée.",
                            url=url,
                            evidence=f"{len(html)} caractères",
                            remediation="Vérifier le rendu côté serveur et les erreurs JavaScript.",
                        )
                    )

                soup = BeautifulSoup(html, "html.parser")

                if not soup.title or not soup.title.text.strip():
                    findings.append(
                        AgentFinding(
                            severity="low",
                            category="seo",
                            title="Balise <title> absente ou vide",
                            description="Le titre de page améliore l'accessibilité et le référencement.",
                            url=url,
                            remediation="Ajouter un <title> descriptif unique par page.",
                        )
                    )

                for href in self._extract_links(soup, url):
                    if href not in visited and len(discovered) < ctx.max_pages * 3:
                        discovered.append(href)
                        if self._same_origin(href, origin):
                            queue.append(href)

            # Vérification des liens (morts)
            for link in self._unique(discovered)[: ctx.max_links]:
                if links_checked >= ctx.max_links:
                    break
                links_checked += 1
                try:
                    probe = await client.head(link)
                    if probe.status_code in (405, 501):
                        probe = await client.get(link)
                except httpx.HTTPError:
                    findings.append(
                        AgentFinding(
                            severity="medium",
                            category="liens",
                            title="Lien inaccessible",
                            description="La ressource liée n'a pas pu être contactée.",
                            url=link,
                            remediation="Corriger ou supprimer le lien.",
                        )
                    )
                    continue
                if probe.status_code >= 400:
                    findings.append(
                        AgentFinding(
                            severity="medium",
                            category="liens",
                            title=f"Lien mort (HTTP {probe.status_code})",
                            description="Le lien pointe vers une ressource inexistante.",
                            url=link,
                            evidence=f"status={probe.status_code}",
                            remediation="Mettre à jour ou supprimer le lien.",
                        )
                    )

        metrics = {
            "pages_checked": pages_checked,
            "links_checked": links_checked,
            "avg_response_ms": round(total_ms / pages_checked) if pages_checked else 0,
        }
        ctx.log.info(
            f"Fiabilité : {pages_checked} page(s), {links_checked} lien(s), {len(findings)} anomalie(s)"
        )
        return AgentReport(agent=self.name, findings=findings, metrics=metrics)

    # ------------------------------------------------------------------
    async def _load_robots(self, client: httpx.AsyncClient, origin: str, ctx: AgentContext) -> None:
        try:
            response = await client.get(f"{origin}/robots.txt")
            if response.status_code == 200:
                cache_robots(origin, parse_robots(response.text))
        except httpx.HTTPError:
            ctx.log.info("robots.txt indisponible — crawl autorisé par défaut")

    @staticmethod
    def _origin(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _same_origin(url: str, origin: str) -> bool:
        return url.startswith(origin + "/") or url == origin

    @staticmethod
    def _extract_links(soup: BeautifulSoup, base: str) -> list[str]:
        links: list[str] = []
        for tag, attr in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
            for element in soup.find_all(tag):
                raw = element.get(attr)
                if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                    continue
                absolute = urljoin(base, raw.strip())
                if absolute.startswith(("http://", "https://")):
                    links.append(absolute.split("#")[0])
        return links

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
