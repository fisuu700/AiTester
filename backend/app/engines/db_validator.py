"""Validateur Données : exécution immédiate de requêtes SELECT (lecture seule)
générées par l'IA après chaque action critique, afin de garantir la cohérence
et l'intégrité des transactions financières.

Support : SQLAlchemy (SQLite, PostgreSQL). Le garde-fou refuse tout statement
non-SELECT avant exécution.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.ai.router import MultiModelRouter
from app.schemas import DBVerification


class DBValidator:
    def __init__(self, logger) -> None:
        self.log = logger
        self._engine: Optional[Engine] = None
        self._url: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._engine is not None

    def connect(self, url: str) -> None:
        if self._engine is not None and self._url == url:
            return
        if self._engine is not None:
            self._engine.dispose()
        self._engine = create_engine(url, pool_pre_ping=True)
        self._url = url
        self.log.info(f"Connecteur DB initialisé (lecture seule) : {self._masked_url(url)}")

    @staticmethod
    def _masked_url(url: str) -> str:
        # Masque les credentials éventuels
        if "://" in url and "@" in url:
            scheme_sep = url.find("://") + 3
            at = url.rfind("@")
            if at > scheme_sep:
                return url[:scheme_sep] + "***@" + url[at + 1 :]
        return url

    def close(self) -> None:
        if self._engine is not None:
            try:
                self._engine.dispose()
            except Exception:  # noqa: BLE001
                pass
            self._engine = None

    def get_schema_hint(self) -> str:
        """Détection du schéma (tables/colonnes) pour guider l'IA."""
        if not self._engine:
            return "inconnu"
        try:
            with self._engine.connect() as conn:
                insp = None
                from sqlalchemy import inspect

                insp = inspect(conn)
                tables = insp.get_table_names()
                parts = []
                for table in tables[:20]:
                    cols = [c["name"] for c in insp.get_columns(table)]
                    parts.append(f"{table}({', '.join(cols)})")
                return "; ".join(parts) if parts else "aucune table trouvée"
        except Exception as exc:  # noqa: BLE001
            self.log.warning(f"Échec de l'introspection du schéma : {exc}")
            return "inconnu"

    async def verify(self, query: str, schema_hint: str = "") -> DBVerification:
        """Valide la requête (garde-fou), l'exécute et retourne les lignes.

        Si `query` est vide et que `schema_hint` est fourni, la requête est
        régénérée par l'IA (rôle qwen2.5-coder).
        """
        if not self._engine:
            return DBVerification(query=query or "", rows=[], ok=False, error="Base de données non connectée")

        final_query = query
        if not final_query and schema_hint:
            router = MultiModelRouter(logger=self.log)
            final_query = await router.generate_db_check(instruction=schema_hint, schema_hint=schema_hint)
        if not final_query:
            return DBVerification(query="", rows=[], ok=False, error="Aucune requête SQL disponible")

        valid, reason = MultiModelRouter.validate_readonly_sql(final_query)
        if not valid:
            self.log.warning(f"Requête refusée par le garde-fou : {final_query[:120]} — {reason}")
            return DBVerification(query=final_query, rows=[], ok=False, error=f"GARDE-FOU : {reason}")

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(final_query))
                keys = list(result.keys())
                rows = [dict(zip(keys, row)) for row in result.fetchmany(50)]
                for row in rows:
                    for key, value in row.items():
                        if isinstance(value, (bytes, bytearray)):
                            row[key] = value.decode("utf-8", "replace")
            self.log.info(
                f"DB check OK ({len(rows)} lignes)",
                layer=None,
                data={"query": final_query[:200], "row_count": len(rows)},
            )
            return DBVerification(query=final_query, rows=rows, row_count=len(rows), ok=True)
        except Exception as exc:  # noqa: BLE001
            self.log.error(f"Échec de la requête SQL : {exc}", data={"query": final_query[:200]})
            return DBVerification(query=final_query, rows=[], ok=False, error=str(exc))
