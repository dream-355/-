from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "知衡健康")
    app_secret: str = os.getenv("APP_SECRET", "dev-only-secret")
    session_days: int = int(os.getenv("SESSION_DAYS", "14"))
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    auth_rate_limit_per_minute: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "10"))
    review_llm_enabled: bool = os.getenv("REVIEW_LLM_ENABLED", "true").lower() == "true"
    database_path: Path = Path(
        os.getenv("DATABASE_PATH", str(ROOT_DIR / "data" / "qihuang.db"))
    )
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7689")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    ).rstrip("/")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_vision_model: str = os.getenv(
        "DEEPSEEK_VISION_MODEL", "deepseek-flash"
    )
    deepseek_timeout: int = int(os.getenv("DEEPSEEK_TIMEOUT", "45"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "知衡健康")
    smtp_starttls: bool = os.getenv("SMTP_STARTTLS", "true").lower() == "true"
    smtp_ssl: bool = os.getenv("SMTP_SSL", "false").lower() == "true"
    smtp_timeout: int = int(os.getenv("SMTP_TIMEOUT", "15"))
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    frontend_dir: Path = ROOT_DIR / "frontend"


settings = Settings()

