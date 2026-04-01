from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.v1.api.deps import get_current_user, require_minimum_plan
from app.v1.models.enums import UserPlan
from app.v1.services.supabase_auth_service import SupabaseAuthService


def test_auth_routes_are_served_from_v1_api(monkeypatch):
    monkeypatch.setattr(
        'app.v1.api.auth.SupabaseAuthService.public_auth_config',
        lambda: SimpleNamespace(
            configured=True,
            auth_provider='supabase',
            supabase_url='https://example.supabase.co',
            publishable_key='anon-key',
            site_url='https://app.inquira.dev',
            manage_account_url='https://account.inquira.dev',
        ),
    )
    monkeypatch.setattr(
        'app.v1.api.auth.SupabaseAuthService.manage_account_url',
        lambda: 'https://account.inquira.dev',
    )
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id='local-user',
        username='Local User',
        email='',
        plan='FREE',
        is_authenticated=False,
        is_guest=True,
        auth_provider='local',
    )
    try:
        client = TestClient(app)
        config_response = client.get('/api/v1/auth/config')
        assert config_response.status_code == 200
        assert config_response.json()['configured'] is True

        me_response = client.get('/api/v1/auth/me')
        assert me_response.status_code == 200
        payload = me_response.json()
        assert payload['user_id'] == 'local-user'
        assert payload['plan'] == 'FREE'
        assert payload['is_guest'] is True

        logout_response = client.post('/api/v1/auth/logout')
        assert logout_response.status_code == 200
        assert logout_response.json()['message'] == 'Session cleared locally.'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_require_minimum_plan_blocks_free_users():
    dependency = require_minimum_plan(UserPlan.PRO)

    with pytest.raises(Exception) as exc_info:
        await dependency(
            current_user=SimpleNamespace(
                id='local-user',
                plan='FREE',
                username='Local User',
            )
        )

    assert getattr(exc_info.value, 'status_code', None) == 403
    assert 'PRO' in str(getattr(exc_info.value, 'detail', ''))


@pytest.mark.asyncio
async def test_require_minimum_plan_allows_enterprise_users():
    dependency = require_minimum_plan(UserPlan.PRO)

    current_user = SimpleNamespace(id='user-1', plan='ENTERPRISE', username='Ada')
    result = await dependency(current_user=current_user)

    assert result is current_user


def test_supabase_plan_order_matches_expected_tiers():
    assert SupabaseAuthService.plan_rank('FREE') < SupabaseAuthService.plan_rank('PRO')
    assert SupabaseAuthService.plan_rank('PRO') < SupabaseAuthService.plan_rank('ENTERPRISE')
    assert SupabaseAuthService.has_minimum_plan('ENTERPRISE', 'PRO') is True
    assert SupabaseAuthService.has_minimum_plan('FREE', 'PRO') is False
