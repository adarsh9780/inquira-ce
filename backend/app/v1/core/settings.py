"""Runtime settings for API v1.

This module centralizes configuration so infrastructure can switch between
SQLite and Postgres with environment changes only.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(backend_root / ".env")
    load_dotenv(repo_root / ".env")


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _load_public_supabase_config_from_toml() -> dict[str, str]:
    candidates: list[Path] = []
    configured_path = str(os.getenv("INQUIRA_TOML_PATH") or "").strip()
    if configured_path:
        candidates.append(Path(configured_path))

    repo_root = Path(__file__).resolve().parents[4]
    candidates.append(repo_root / "inquira.toml")

    for path in candidates:
        if not path.exists():
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        supabase = (
            data.get("auth", {})
            .get("supabase", {})
        )
        if not isinstance(supabase, dict):
            continue
        return {
            "url": str(supabase.get("url") or "").strip(),
            "publishable_key": str(supabase.get("publishable_key") or "").strip(),
        }

    return {"url": "", "publishable_key": ""}


_load_env_files()


@dataclass(frozen=True)
class V1Settings:
    """Immutable configuration values for v1 services."""

    auth_db_url: str
    appdata_db_url: str
    reset_enabled: bool
    reset_token: str
    allow_schema_bootstrap: bool
    auth_provider: str
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str

    @staticmethod
    def load() -> "V1Settings":
        """Load settings from environment variables.

        Returns:
            V1Settings object with DB URLs and reset command guards.
        """

        default_dir = Path.home() / ".inquira"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_auth_db = f"sqlite+aiosqlite:///{default_dir / 'auth_v1.db'}"
        default_appdata_db = f"sqlite+aiosqlite:///{default_dir / 'appdata_v1.db'}"
        public_supabase = _load_public_supabase_config_from_toml()

        return V1Settings(
            auth_db_url=os.getenv("INQUIRA_AUTH_DB_URL", default_auth_db),
            appdata_db_url=os.getenv("INQUIRA_APPDATA_DB_URL", default_appdata_db),
            reset_enabled=os.getenv("INQUIRA_ENABLE_RESET", "0") == "1",
            reset_token=os.getenv("INQUIRA_RESET_TOKEN", ""),
            allow_schema_bootstrap=os.getenv("INQUIRA_ALLOW_SCHEMA_BOOTSTRAP", "0") == "1",
            auth_provider=os.getenv("INQUIRA_AUTH_PROVIDER", "sqlite").strip().lower(),
            supabase_url=_first_env(
                "INQUIRA_SUPABASE_URL",
                "SB_INQUIRA_CE_URL",
                default=public_supabase["url"],
            ),
            supabase_publishable_key=_first_env(
                "INQUIRA_SUPABASE_PUBLISHABLE_KEY",
                "SB_INQUIRA_CE_PUBLISHABLE_KEY",
                default=public_supabase["publishable_key"],
            ),
            supabase_secret_key=_first_env(
                "INQUIRA_SUPABASE_SECRET_KEY",
                "SB_INQUIRA_CE_SECRET_KEY",
                "INQUIRA_SUPABASE_SERVICE_ROLE_KEY",
                "SB_INQUIRA_CE_SERVICE_ROLE_KEY",
            ),
        )


settings = V1Settings.load()
