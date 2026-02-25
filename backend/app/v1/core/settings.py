"""Runtime settings for API v1.

This module centralizes configuration so infrastructure can switch between
SQLite and Postgres with environment changes only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class V1Settings:
    """Immutable configuration values for v1 services."""

    database_url: str
    reset_enabled: bool
    reset_token: str
    allow_schema_bootstrap: bool
    auth_provider: str

    @staticmethod
    def load() -> "V1Settings":
        """Load settings from environment variables.

        Returns:
            V1Settings object with DB URL and reset command guards.
        """

        default_sqlite_path = Path.home() / ".inquira" / "app_v1.db"
        default_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        default_db = f"sqlite+aiosqlite:///{default_sqlite_path}"

        return V1Settings(
            database_url=os.getenv("INQUIRA_DB_URL", default_db),
            reset_enabled=os.getenv("INQUIRA_ENABLE_RESET", "0") == "1",
            reset_token=os.getenv("INQUIRA_RESET_TOKEN", ""),
            allow_schema_bootstrap=os.getenv("INQUIRA_ALLOW_SCHEMA_BOOTSTRAP", "0") == "1",
            auth_provider=os.getenv("INQUIRA_AUTH_PROVIDER", "sqlite").strip().lower(),
        )


settings = V1Settings.load()
