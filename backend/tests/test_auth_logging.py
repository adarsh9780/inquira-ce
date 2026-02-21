from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.auth import get_current_user


def test_get_current_user_does_not_log_cookies_when_missing_session(monkeypatch):
    """Regression: avoid noisy/sensitive cookie logging for expected 401 paths."""
    from app.api import auth as auth_module

    calls = []

    def _fake_logprint(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(auth_module, "logprint", _fake_logprint)

    request = SimpleNamespace(cookies={})

    with pytest.raises(HTTPException) as exc:
        get_current_user(request)

    assert exc.value.status_code == 401
    assert calls == []
