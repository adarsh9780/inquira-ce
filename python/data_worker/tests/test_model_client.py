from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from inquira_data_worker.model_client import ModelSettings, create_model_client


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_anthropic_schema_client_uses_native_messages_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def urlopen(request: Any, timeout: int) -> _Response:
        captured["url"] = request.full_url
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"content": [{"type": "text", "text": '{"columns": []}'}]})

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    client = create_model_client({
        "provider": "anthropic",
        "model": "claude-test",
        "api_key": "anthropic-secret",
        "base_url": "",
        "max_tokens": 512,
        "temperature": 0.1,
    })
    result = asyncio.run(client.complete([
        {"role": "system", "content": "Return JSON."},
        {"role": "user", "content": "Describe amount."},
    ]))

    assert result == '{"columns": []}'
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "anthropic-secret"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert "authorization" not in captured["headers"]
    assert captured["body"]["system"] == "Return JSON."
    assert captured["body"]["messages"] == [{"role": "user", "content": "Describe amount."}]
    assert captured["body"]["max_tokens"] == 512


@pytest.mark.parametrize("provider", ["openai", "openrouter", "anthropic"])
def test_remote_schema_clients_require_api_keys(provider: str) -> None:
    with pytest.raises(ValueError, match="API key"):
        ModelSettings.from_dict({
            "provider": provider,
            "model": "model",
            "api_key": "",
            "base_url": "https://example.test" if provider != "anthropic" else "",
        })
