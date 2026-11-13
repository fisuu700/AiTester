from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Toujours charger backend/.env, quel que soit le répertoire de lancement.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI E2E Testing Agent"
    app_version: str = "2.0.0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120

    model_planner: str = "llama3.1:8b"
    model_executor: str = "qwen2.5-coder:7b"
    model_analyst: str = "deepseek-r1:7b"

    browser_headless: bool = True
    browser_timeout_ms: int = 30000

    cors_origins: str = "http://localhost:3000"

    reports_dir: str = "reports"
    screenshots_dir: str = "reports/screenshots"

    reports_url_prefix: str = "/reports"

    # --- Plateforme -------------------------------------------------
    database_url: str = "sqlite:///./platform.db"

    jwt_secret: str = "change-me-in-production-please-use-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 jours

    # Garde-fou anti-SSRF : autorise localhost / IP privées (démo uniquement)
    allow_private_targets: bool = False

    max_pages_per_scan: int = 20
    max_links_checked: int = 40
    scan_timeout_seconds: int = 900
    agent_timeout_seconds: int = 300
    max_concurrent_scans: int = 3

    user_agent: str = "AITesterBot/1.0 (+https://example.tn/ai-tester)"
    request_timeout_seconds: int = 15

    # Pondération du score global
    score_weights: str = "reliability=0.30,security=0.35,performance=0.20,accessibility=0.15"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def weights(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for item in self.score_weights.split(","):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            try:
                result[key.strip()] = float(value)
            except ValueError:
                continue
        return result or {"reliability": 0.30, "security": 0.35, "performance": 0.20, "accessibility": 0.15}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
