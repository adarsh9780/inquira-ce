from types import SimpleNamespace

import pytest

from app.v1.repositories.auth_repository_factory import get_auth_repository
from app.v1.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from app.v1.repositories.supabase_auth_repository import SupabaseAuthRepository


def test_factory_returns_sqlalchemy_repository(monkeypatch):
    monkeypatch.setattr(
        "app.v1.repositories.auth_repository_factory.settings",
        SimpleNamespace(auth_provider="sqlite"),
    )
    repo = get_auth_repository(session=object())
    assert isinstance(repo, SqlAlchemyAuthRepository)


def test_factory_returns_supabase_repository(monkeypatch):
    monkeypatch.setattr(
        "app.v1.repositories.auth_repository_factory.settings",
        SimpleNamespace(auth_provider="supabase"),
    )
    repo = get_auth_repository(session=object())
    assert isinstance(repo, SupabaseAuthRepository)


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(
        "app.v1.repositories.auth_repository_factory.settings",
        SimpleNamespace(auth_provider="mystery"),
    )
    with pytest.raises(RuntimeError) as exc:
        get_auth_repository(session=object())
    assert "Unsupported INQUIRA_AUTH_PROVIDER" in str(exc.value)
