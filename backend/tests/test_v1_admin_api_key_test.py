import pytest
from fastapi import HTTPException

from app.v1.api.admin import GeminiTestRequest, test_gemini_api_key as run_gemini_api_key_test


@pytest.mark.asyncio
async def test_test_gemini_api_key_uses_selected_model(monkeypatch):
    captured = {}

    class FakeLLMService:
        def __init__(self, api_key: str, model: str):
            captured["api_key"] = api_key
            captured["model"] = model

        def ask(self, _prompt: str, _fmt, max_tokens: int | None = None):
            captured["max_tokens"] = max_tokens
            return "OK"

    monkeypatch.setattr("app.v1.api.admin.LLMService", FakeLLMService)

    payload = GeminiTestRequest(api_key="test-key", model="openai/gpt-4o-mini")
    response = await run_gemini_api_key_test(payload)

    assert response["detail"] == "API key is valid and working correctly"
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["max_tokens"] == 8


@pytest.mark.asyncio
async def test_test_gemini_api_key_maps_provider_model_rejection_to_400(monkeypatch):
    class FakeLLMService:
        def __init__(self, **_kwargs):
            pass

        def ask(self, _prompt: str, _fmt, max_tokens: int | None = None):
            raise HTTPException(status_code=404, detail="No route for model")

    monkeypatch.setattr("app.v1.api.admin.LLMService", FakeLLMService)

    payload = GeminiTestRequest(api_key="test-key", model="google/gemini-2.5-flash")
    with pytest.raises(HTTPException) as exc:
        await run_gemini_api_key_test(payload)

    assert exc.value.status_code == 400
    assert "Provider rejected model" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_test_gemini_api_key_does_not_remap_generic_500_to_quota(monkeypatch):
    class FakeLLMService:
        def __init__(self, **_kwargs):
            pass

        def ask(self, _prompt: str, _fmt, max_tokens: int | None = None):
            raise HTTPException(status_code=500, detail="local parser limit reached")

    monkeypatch.setattr("app.v1.api.admin.LLMService", FakeLLMService)

    payload = GeminiTestRequest(api_key="test-key", model="google/gemini-2.5-flash")
    with pytest.raises(HTTPException) as exc:
        await run_gemini_api_key_test(payload)

    assert exc.value.status_code == 500
    assert "Error testing API key: local parser limit reached" in str(exc.value.detail)
