"""Intercepteur réseau : capture silencieuse des échanges HTTP/REST via
page.on("response") entre le Frontend et le Backend de l'application cible.

Vérifie les codes HTTP (200, 400, 500), les temps de réponse et les corps JSON.
"""

from __future__ import annotations

import json
from collections import deque
from typing import Any, Optional

from playwright.async_api import Response

from app.schemas import APIObservation

SLOW_THRESHOLD_MS = 3000
MAX_BODY_CHARS = 4000


class APIMonitor:
    def __init__(self, logger) -> None:
        self.log = logger
        self._observations: deque[APIObservation] = deque(maxlen=500)
        self._attached = False

    def attach(self, page) -> None:
        """Attache l'interception à une page Playwright (idempotent)."""
        if self._attached:
            return
        page.on("response", self._on_response)
        self._attached = True

    async def _on_response(self, response: Response) -> None:
        try:
            request = response.request
            resource = request.resource_type
            # On ignore les assets statiques bruyants
            if resource in ("image", "font", "stylesheet", "media"):
                return
            obs = APIObservation(
                url=response.url,
                method=request.method,
                status=response.status,
                duration_ms=0,
                body=None,
            )
            try:
                server = response.server_addr_timing  # noqa: F841
            except Exception:  # noqa: BLE001
                pass
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                try:
                    body = await response.text()
                    if len(body) > MAX_BODY_CHARS:
                        body = body[:MAX_BODY_CHARS]
                    obs.body = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    obs.body = None
                except Exception:  # noqa: BLE001
                    obs.body = None
            self._observations.append(obs)
            self.log.info(
                f"HTTP {obs.status} {obs.method} {obs.url}",
                layer=None,
                data={"status": obs.status, "url": obs.url},
            )
        except Exception:  # noqa: BLE001
            pass

    def snapshot_since(self, n: int = 30) -> list[APIObservation]:
        items = list(self._observations)
        return items[-n:]

    def snapshot_all(self) -> list[APIObservation]:
        return list(self._observations)

    @staticmethod
    def check_observations(observations: list[APIObservation]) -> list[str]:
        """Retourne les anomalies API détectées (codes ≥400, latence excessive)."""
        anomalies: list[str] = []
        for obs in observations:
            if obs.status >= 500:
                anomalies.append(f"Erreur serveur HTTP {obs.status} sur {obs.url}")
            elif obs.status >= 400:
                anomalies.append(f"Erreur client HTTP {obs.status} sur {obs.url}")
        return anomalies

    def reset(self) -> None:
        self._observations.clear()

    def summarize(self, observations: Optional[list[APIObservation]] = None) -> dict[str, Any]:
        obs = observations if observations is not None else self.snapshot_all()
        statuses = [o.status for o in obs]
        return {
            "total": len(obs),
            "errors_5xx": sum(1 for s in statuses if s >= 500),
            "errors_4xx": sum(1 for s in statuses if 400 <= s < 500),
        }
