from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.v1.api.deps import get_current_user, require_minimum_plan
from app.v1.models.enums import UserPlan
from app.v1.services.local_auth_service import LocalAuthService


def test_auth_routes_are_local_only_in_v1_api():
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
        config_payload = config_response.json()
        assert config_payload['configured'] is False
        assert config_payload['auth_provider'] == 'local'
        external_provider_url_key = ''.join(['supa', 'base', '_url'])
        external_public_client_key = ''.join(['publish', 'able_key'])
        assert external_provider_url_key not in config_payload
        assert external_public_client_key not in config_payload

        me_response = client.get('/api/v1/auth/me')
        assert me_response.status_code == 200
        payload = me_response.json()
        assert payload['user_id'] == 'local-user'
        assert payload['plan'] == 'FREE'
        assert payload['is_guest'] is True
        assert payload['auth_provider'] == 'local'
        assert payload['manage_account_url'] == ''

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


def test_local_plan_order_matches_expected_tiers():
    assert LocalAuthService.plan_rank('FREE') < LocalAuthService.plan_rank('PRO')
    assert LocalAuthService.plan_rank('PRO') < LocalAuthService.plan_rank('ENTERPRISE')
    assert LocalAuthService.has_minimum_plan('ENTERPRISE', 'PRO') is True
    assert LocalAuthService.has_minimum_plan('FREE', 'PRO') is False


@pytest.mark.asyncio
async def test_bearer_token_still_resolves_to_local_user():
    user = await LocalAuthService.resolve_current_user("Bearer signed-in-token")

    assert user.is_guest is True
    assert user.is_authenticated is False
    assert user.auth_provider == 'local'
    assert user.id == "local-user"


@pytest.mark.asyncio
async def test_anonymous_session_remains_local_user():
    user = await LocalAuthService.resolve_current_user(None)

    assert user.is_guest is True
    assert user.id == "local-user"
