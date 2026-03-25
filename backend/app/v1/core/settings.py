"""Runtime settings for API v1.

This module centralizes configuration so infrastructure can switch between
SQLite and Postgres with environment changes only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(backend_root / ".env")
    load_dotenv(repo_root / ".env")


_load_env_files()


@dataclass(frozen=True)
class V1Settings:
    """Immutable configuration values for v1 services."""

    auth_db_url: str
    appdata_db_url: str
    reset_enabled: bool
    reset_token: str
    allow_schema_bootstrap: bool

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

        return V1Settings(
            auth_db_url=os.getenv("INQUIRA_AUTH_DB_URL", default_auth_db),
            appdata_db_url=os.getenv("INQUIRA_APPDATA_DB_URL", default_appdata_db),
            reset_enabled=os.getenv("INQUIRA_ENABLE_RESET", "0") == "1",
            reset_token=os.getenv("INQUIRA_RESET_TOKEN", ""),
            allow_schema_bootstrap=os.getenv("INQUIRA_ALLOW_SCHEMA_BOOTSTRAP", "0") == "1",
        )


settings = V1Settings.load()

