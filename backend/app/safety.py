"""Garde-fous de sécurité pour le scan d'URL tierces.

- normalisation d'URL
- protection anti-SSRF (localhost, IP privées, métadonnées cloud)
- lecture / respect de robots.txt
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse

from app.config import settings

_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "host.docker.internal",
    "metadata.google.internal",
    "metadata",
}

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class TargetNotAllowed(ValueError):
    """Cible refusée par la politique de sécurité."""


def normalize_url(raw: str) -> str:
    """Retourne une URL canonique (scheme + host + path), sans query ni fragment."""
    value = (raw or "").strip()
    if not value:
        raise TargetNotAllowed("URL vide.")
    if not _SCHEME_RE.match(value):
        value = "https://" + value

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise TargetNotAllowed("Seuls les schémas http et https sont acceptés.")
    if not parsed.hostname:
        raise TargetNotAllowed("URL invalide : hôte manquant.")

    path = parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return any(ip in network for network in BLOCKED_NETWORKS)


def _resolves_to_blocked(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False  # hôte non résolu : le scan échouera proprement

    for info in infos:
        raw_ip = info[4][0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            return True
    return False


def assert_target_allowed(url: str) -> str:
    """Valide une cible et retourne son URL normalisée.

    Lève TargetNotAllowed si la cible est interdite.
    """
    normalized = normalize_url(url)
    hostname = urlparse(normalized).hostname or ""

    if settings.allow_private_targets:
        return normalized

    if hostname in BLOCKED_HOSTNAMES:
        raise TargetNotAllowed(
            "Les adresses locales sont interdites. Activez ALLOW_PRIVATE_TARGETS=true pour la démo locale."
        )

    try:
        ip = ipaddress.ip_address(hostname)
        if _is_blocked_ip(ip):
            raise TargetNotAllowed("Les adresses IP privées / réservées sont interdites.")
        return normalized
    except ValueError:
        pass

    if _resolves_to_blocked(hostname):
        raise TargetNotAllowed(
            "Cette URL résout vers une adresse privée (protection anti-SSRF)."
        )

    return normalized


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------

_ROBOTS_CACHE: dict[str, list[str]] = {}


def parse_robots(text: str) -> list[str]:
    """Extrait les directives Disallow du groupe `User-agent: *`."""
    rules: list[str] = []
    active = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            active = value == "*"
        elif key == "disallow" and active and value:
            rules.append(value)
    return rules


def is_path_allowed(path: str, rules: list[str]) -> bool:
    if not rules:
        return True
    for rule in rules:
        if rule == "/":
            return False
        prefix = rule.rstrip("*")
        if path.startswith(prefix):
            return False
    return True


def cache_robots(origin: str, rules: list[str]) -> None:
    _ROBOTS_CACHE[origin] = rules


def get_cached_robots(origin: str) -> list[str]:
    return _ROBOTS_CACHE.get(origin, [])
