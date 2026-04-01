"""Runtime settings for API v1.

This module centralizes configuration so infrastructure can switch between
SQLite and Postgres with environment changes only.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv



def _load_env_files() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(backend_root / ".env")
    load_dotenv(repo_root / ".env")


_load_env_files()



def _deep_get(mapping: dict[str, Any], *keys: str) -> str:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return str(current or "").strip()



def _resolve_runtime_toml_path() -> Path | None:
    explicit = str(os.getenv("INQUIRA_TOML_PATH") or "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            return candidate

    repo_root = Path(__file__).resolve().parents[4]
    candidate = repo_root / "inquira.toml"
    return candidate if candidate.exists() else None



def _load_runtime_toml() -> dict[str, Any]:
    config_path = _resolve_runtime_toml_path()
    if config_path is None:
        return {}
    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


_RUNTIME_TOML = _load_runtime_toml()



def _env_or_toml(env_name: str, toml_keys: tuple[str, ...] = ()) -> str:
    env_value = str(os.getenv(env_name) or "").strip()
    if env_value:
        return env_value
    if toml_keys:
        return _deep_get(_RUNTIME_TOML, *toml_keys)
    return ""


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
    supabase_auth_redirect_uri: str
    supabase_site_url: str
    supabase_manage_account_url: str
    supabase_plan_table: str

    @staticmethod
    def load() -> "V1Settings":
        default_dir = Path.home() / ".inquira"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_auth_db = f"sqlite+aiosqlite:///{default_dir / 'auth_v1.db'}"
        default_appdata_db = f"sqlite+aiosqlite:///{default_dir / 'appdata_v1.db'}"

        supabase_url = (
            _env_or_toml("SB_INQUIRA_CE_URL")
            or _env_or_toml("INQUIRA_SUPABASE_URL")
            or _env_or_toml("INQUIRA_SUPABASE_PROJECT_URL", ("auth", "supabase", "url"))
        )
        publishable_key = (
            _env_or_toml("SB_INQUIRA_CE_PUBLISHABLE_KEY")
            or _env_or_toml("INQUIRA_SUPABASE_PUBLISHABLE_KEY")
            or _env_or_toml("INQUIRA_SUPABASE_ANON_KEY", ("auth", "supabase", "publishable_key"))
        )
        secret_key = (
            _env_or_toml("SB_INQUIRA_CE_SECRET_KEY")
            or _env_or_toml("INQUIRA_SUPABASE_SECRET_KEY")
        )
        redirect_uri = (
            _env_or_toml("SB_INQUIRA_CE_AUTH_REDIRECT_URI")
            or _env_or_toml("INQUIRA_SUPABASE_AUTH_REDIRECT_URI")
        )
        site_url = (
            _env_or_toml("SB_INQUIRA_CE_SITE_URL")
            or _env_or_toml("INQUIRA_SUPABASE_SITE_URL")
        )
        manage_url = (
            _env_or_toml("SB_INQUIRA_CE_MANAGE_ACCOUNT_URL")
            or _env_or_toml("INQUIRA_SUPABASE_MANAGE_ACCOUNT_URL")
            or site_url
        )

        return V1Settings(
            auth_db_url=os.getenv("INQUIRA_AUTH_DB_URL", default_auth_db),
            appdata_db_url=os.getenv("INQUIRA_APPDATA_DB_URL", default_appdata_db),
            reset_enabled=os.getenv("INQUIRA_ENABLE_RESET", "0") == "1",
            reset_token=os.getenv("INQUIRA_RESET_TOKEN", ""),
            allow_schema_bootstrap=os.getenv("INQUIRA_ALLOW_SCHEMA_BOOTSTRAP", "0") == "1",
            auth_provider=str(os.getenv("INQUIRA_AUTH_PROVIDER") or "supabase").strip().lower() or "supabase",
            supabase_url=supabase_url,
            supabase_publishable_key=publishable_key,
            supabase_secret_key=secret_key,
            supabase_auth_redirect_uri=redirect_uri,
            supabase_site_url=site_url,
            supabase_manage_account_url=manage_url,
            supabase_plan_table=str(os.getenv("SB_INQUIRA_CE_PLAN_TABLE") or "account_plans").strip() or "account_plans",
        )


settings = V1Settings.load()
