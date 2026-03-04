from types import SimpleNamespace

import pytest

from app.v1.api.deps import ensure_appdata_principal
from app.v1.core.settings import V1Settings


def test_v1_settings_load_reads_split_db_env_vars(monkeypatch):
    monkeypatch.setenv("INQUIRA_AUTH_DB_URL", "sqlite+aiosqlite:////tmp/auth-test.db")
    monkeypatch.setenv("INQUIRA_APPDATA_DB_URL", "sqlite+aiosqlite:////tmp/appdata-test.db")
    monkeypatch.setenv("INQUIRA_ENABLE_RESET", "1")
    monkeypatch.setenv("INQUIRA_RESET_TOKEN", "token-1")
    monkeypatch.setenv("INQUIRA_ALLOW_SCHEMA_BOOTSTRAP", "1")
    monkeypatch.setenv("INQUIRA_AUTH_PROVIDER", "sqlite")

    loaded = V1Settings.load()

    assert loaded.auth_db_url == "sqlite+aiosqlite:////tmp/auth-test.db"
    assert loaded.appdata_db_url == "sqlite+aiosqlite:////tmp/appdata-test.db"
    assert loaded.reset_enabled is True
    assert loaded.reset_token == "token-1"
    assert loaded.allow_schema_bootstrap is True


@pytest.mark.asyncio
async def test_ensure_appdata_principal_falls_back_to_user_id_when_username_missing(monkeypatch):
    captured = {}

    async def fake_get_or_create(*, session, principal_id, username, plan):
        captured["session"] = session
        captured["principal_id"] = principal_id
        captured["username"] = username
        captured["plan"] = plan
        return SimpleNamespace(id=principal_id, username_cached=username, plan_cached=plan)

    monkeypatch.setattr(
        "app.v1.api.deps.PrincipalRepository.get_or_create",
        fake_get_or_create,
    )

    class FakeSession:
        def __init__(self):
            self.new = {object()}
            self.dirty = set()
            self.commits = 0

        async def commit(self):
            self.commits += 1

    fake_session = FakeSession()
    principal = await ensure_appdata_principal(
        appdata_session=fake_session,
        current_user=SimpleNamespace(id="user-42", plan="FREE"),
    )

    assert principal.id == "user-42"
    assert captured["principal_id"] == "user-42"
    assert captured["username"] == "user-42"
    assert captured["plan"] == "FREE"
    assert fake_session.commits == 1
