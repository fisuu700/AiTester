"""Agent de sécurité — analyse strictement PASSIVE.

Aucune tentative d'intrusion : on se limite à ce que le serveur expose
publiquement (en-têtes, TLS, cookies, fichiers de configuration oubliés).
"""

from __future__ import annotations

import re
import socket
import ssl
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

from app.agents.base import AgentContext, AgentFinding, AgentReport, BaseAgent

SECURITY_HEADERS = [
    (
        "strict-transport-security",
        "medium",
        "HSTS absent",
        "Ajouter `Strict-Transport-Security: max-age=31536000; includeSubDomains`.",
    ),
    (
        "content-security-policy",
        "high",
        "Content-Security-Policy absente",
        "Définir une CSP restrictive pour limiter les injections de scripts.",
    ),
    (
        "x-frame-options",
        "medium",
        "X-Frame-Options absent",
        "Ajouter `X-Frame-Options: DENY` (ou une directive CSP frame-ancestors).",
    ),
    (
        "x-content-type-options",
        "low",
        "X-Content-Type-Options absent",
        "Ajouter `X-Content-Type-Options: nosniff`.",
    ),
    (
        "referrer-policy",
        "low",
        "Referrer-Policy absente",
        "Ajouter `Referrer-Policy: strict-origin-when-cross-origin`.",
    ),
    (
        "permissions-policy",
        "low",
        "Permissions-Policy absente",
        "Restreindre les API navigateur (camera, microphone, geolocation…).",
    ),
]

EXPOSED_FILES = [
    ("/.env", "variables d'environnement", "critical", "API_KEY"),
    ("/.git/config", "dépôt Git exposé", "critical", "[core]"),
    ("/backup.sql", "sauvegarde SQL exposée", "critical", "INSERT INTO"),
    ("/.DS_Store", "métadonnées macOS", "medium", "Bud1"),
    ("/server-status", "statut serveur Apache", "medium", "Apache Server Status"),
    ("/phpinfo.php", "page phpinfo exposée", "high", "PHP Version"),
    ("/actuator/env", "endpoint Spring Actuator", "high", "propertySources"),
]

DISCLOSURE_HEADERS = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator"]

MIXED_CONTENT_RE = re.compile(
    r"""(?:src|href|action)\s*=\s*["']http://[^"']+["']""", re.IGNORECASE
)


class SecurityAgent(BaseAgent):
    name = "security"
    label = "Sécurité"

    async def run(self, ctx: AgentContext) -> AgentReport:
        findings: list[AgentFinding] = []
        parsed = urlparse(ctx.url)
        host = parsed.hostname or ""

        if parsed.scheme != "https":
            findings.append(
                AgentFinding(
                    severity="critical",
                    category="chiffrement",
                    title="Site servi en HTTP (sans TLS)",
                    description="Les échanges circulent en clair et peuvent être interceptés.",
                    url=ctx.url,
                    evidence=f"scheme={parsed.scheme}",
                    remediation="Activer HTTPS avec un certificat valide et rediriger tout le trafic.",
                )
            )
        else:
            findings.extend(self._check_tls(host, ctx))

        headers = {
            "User-Agent": ctx.user_agent,
            "Accept": "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(
            verify=False,
            follow_redirects=True,
            timeout=ctx.request_timeout,
            headers=headers,
            trust_env=False,
        ) as client:
            try:
                response = await client.get(ctx.url)
            except httpx.HTTPError as exc:
                ctx.log.error(f"Impossible d'analyser les en-têtes : {exc}")
                return AgentReport(
                    agent=self.name,
                    status="failed",
                    findings=findings,
                    error=str(exc),
                    score=None,
                )

            findings.extend(self._check_headers(response, ctx.url))
            findings.extend(self._check_cookies(response, ctx.url))
            findings.extend(await self._check_cors(client, ctx.url))
            findings.extend(await self._check_exposed_files(client, ctx, parsed))
            findings.extend(self._check_mixed_content(response, ctx.url))

            if response.status_code == 200:
                ctx.log.info(f"En-têtes analysés (HTTP {response.status_code})")

        ctx.log.info(f"Sécurité : {len(findings)} problème(s) détecté(s)")
        return AgentReport(
            agent=self.name,
            findings=findings,
            metrics={"findings": len(findings)},
        )

    # ------------------------------------------------------------------
    def _check_tls(self, host: str, ctx: AgentContext) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        context = ssl.create_default_context()
        try:
            with socket.create_connection((host, 443), timeout=8) as sock:
                with context.wrap_socket(sock, server_hostname=host) as tls:
                    cert = tls.getpeercert()
                    version = tls.version() or "inconnue"
        except ssl.SSLCertVerificationError as exc:
            return [
                AgentFinding(
                    severity="critical",
                    category="chiffrement",
                    title="Certificat TLS invalide",
                    description=str(exc),
                    url=f"https://{host}",
                    evidence=exc.verify_message if hasattr(exc, "verify_message") else str(exc),
                    remediation="Renouveler le certificat et vérifier la chaîne d'autorités.",
                )
            ]
        except (OSError, ssl.SSLError) as exc:
            return [
                AgentFinding(
                    severity="high",
                    category="chiffrement",
                    title="Connexion TLS impossible",
                    description=str(exc),
                    url=f"https://{host}",
                    remediation="Vérifier la configuration TLS du serveur (port 443).",
                )
            ]

        if version in ("TLSv1", "TLSv1.1", "SSLv3"):
            findings.append(
                AgentFinding(
                    severity="high",
                    category="chiffrement",
                    title=f"Version TLS obsolète ({version})",
                    description="Les protocoles anciens sont vulnérables.",
                    url=f"https://{host}",
                    evidence=f"tls_version={version}",
                    remediation="Forcer TLS 1.2 minimum (idéalement TLS 1.3).",
                )
            )

        not_after = cert.get("notAfter") if cert else None
        if not_after:
            try:
                expiry = parsedate_to_datetime(not_after)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                days_left = (expiry - datetime.now(timezone.utc)).days
                if days_left < 0:
                    findings.append(
                        AgentFinding(
                            severity="critical",
                            category="chiffrement",
                            title="Certificat TLS expiré",
                            description=f"Le certificat a expiré il y a {abs(days_left)} jour(s).",
                            url=f"https://{host}",
                            evidence=f"notAfter={not_after}",
                            remediation="Renouveler immédiatement le certificat.",
                        )
                    )
                elif days_left < 30:
                    findings.append(
                        AgentFinding(
                            severity="medium",
                            category="chiffrement",
                            title="Certificat TLS bientôt expiré",
                            description=f"Expiration dans {days_left} jour(s).",
                            url=f"https://{host}",
                            evidence=f"notAfter={not_after}",
                            remediation="Automatiser le renouvellement (Let's Encrypt / ACME).",
                        )
                    )
            except (TypeError, ValueError):
                pass

        return findings

    def _check_headers(self, response: httpx.Response, url: str) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for header, severity, title, remediation in SECURITY_HEADERS:
            if header == "strict-transport-security" and not url.startswith("https"):
                continue
            if header not in response.headers:
                findings.append(
                    AgentFinding(
                        severity=severity,
                        category="en-têtes",
                        title=title,
                        description=f"L'en-tête `{header}` est absent de la réponse.",
                        url=url,
                        evidence=f"headers={list(response.headers.keys())}",
                        remediation=remediation,
                    )
                )

        for header in DISCLOSURE_HEADERS:
            value = response.headers.get(header)
            if value:
                findings.append(
                    AgentFinding(
                        severity="low",
                        category="divulgation",
                        title=f"En-tête révélateur : {header}",
                        description="Le serveur expose sa technologie et sa version.",
                        url=url,
                        evidence=f"{header}: {value}",
                        remediation="Masquer ou normaliser cet en-tête côté reverse proxy.",
                    )
                )
        return findings

    def _check_cookies(self, response: httpx.Response, url: str) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for raw in response.headers.get_list("set-cookie"):
            name = raw.split("=", 1)[0].strip()
            lowered = raw.lower()
            if "secure" not in lowered:
                findings.append(
                    AgentFinding(
                        severity="medium",
                        category="cookies",
                        title=f"Cookie `{name}` sans flag Secure",
                        description="Le cookie peut être transmis en clair.",
                        url=url,
                        evidence=raw[:200],
                        remediation="Ajouter `Secure` à tous les cookies de session.",
                    )
                )
            if "httponly" not in lowered:
                findings.append(
                    AgentFinding(
                        severity="medium",
                        category="cookies",
                        title=f"Cookie `{name}` sans flag HttpOnly",
                        description="Le cookie est accessible via JavaScript (risque XSS).",
                        url=url,
                        evidence=raw[:200],
                        remediation="Ajouter `HttpOnly` aux cookies de session.",
                    )
                )
            if "samesite" not in lowered:
                findings.append(
                    AgentFinding(
                        severity="low",
                        category="cookies",
                        title=f"Cookie `{name}` sans SameSite",
                        description="Protection CSRF réduite.",
                        url=url,
                        evidence=raw[:200],
                        remediation="Ajouter `SameSite=Lax` ou `Strict`.",
                    )
                )
        return findings

    async def _check_cors(self, client: httpx.AsyncClient, url: str) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        try:
            probe = await client.options(
                url,
                headers={
                    "Origin": "https://evil.example",
                    "Access-Control-Request-Method": "GET",
                },
            )
        except httpx.HTTPError:
            return findings

        allow_origin = probe.headers.get("access-control-allow-origin", "")
        allow_credentials = probe.headers.get("access-control-allow-credentials", "").lower()

        if allow_origin.strip() == "*" and allow_credentials == "true":
            findings.append(
                AgentFinding(
                    severity="critical",
                    category="cors",
                    title="CORS permissif avec credentials",
                    description="N'importe quelle origine peut lire les réponses authentifiées.",
                    url=url,
                    evidence=f"ACAO={allow_origin} ACAC={allow_credentials}",
                    remediation="Restreindre `Access-Control-Allow-Origin` à une liste blanche explicite.",
                )
            )
        elif allow_origin.strip() == "*":
            findings.append(
                AgentFinding(
                    severity="medium",
                    category="cors",
                    title="CORS ouvert à toutes les origines",
                    description="`Access-Control-Allow-Origin: *` autorise toute origine.",
                    url=url,
                    evidence=f"ACAO={allow_origin}",
                    remediation="Limiter aux domaines réellement utilisés.",
                )
            )
        return findings

    async def _check_exposed_files(
        self, client: httpx.AsyncClient, ctx: AgentContext, parsed
    ) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        origin = f"{parsed.scheme}://{parsed.netloc}"
        for path, label, severity, signature in EXPOSED_FILES:
            try:
                response = await client.get(origin + path)
            except httpx.HTTPError:
                continue
            if response.status_code != 200:
                continue
            body = (response.text or "")[:5000]
            if signature and signature not in body:
                continue
            findings.append(
                AgentFinding(
                    severity=severity,
                    category="exposition",
                    title=f"Fichier sensible accessible : {label}",
                    description=f"La ressource `{path}` est publiquement téléchargeable.",
                    url=origin + path,
                    evidence=f"status=200, {len(body)} caractères lus",
                    remediation=f"Bloquer l'accès à `{path}` au niveau du serveur web.",
                )
            )
            ctx.log.warning(f"Fichier sensible exposé : {path}")
        return findings

    def _check_mixed_content(self, response: httpx.Response, url: str) -> list[AgentFinding]:
        if not url.startswith("https"):
            return []
        if "html" not in response.headers.get("content-type", ""):
            return []
        matches = MIXED_CONTENT_RE.findall(response.text or "")
        if not matches:
            return []
        return [
            AgentFinding(
                severity="high",
                category="contenu-mixte",
                title=f"{len(matches)} ressource(s) chargée(s) en HTTP",
                description="Une page HTTPS charge des ressources non chiffrées, cassant la garantie TLS.",
                url=url,
                evidence="; ".join(matches[:5]),
                remediation="Servir toutes les ressources en HTTPS (URL relatives ou https://).",
            )
        ]
