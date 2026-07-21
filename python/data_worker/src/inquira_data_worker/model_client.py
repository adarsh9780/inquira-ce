"""Small async clients for OpenAI-compatible providers and Ollama."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelSettings:
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelSettings":
        provider = str(value.get("provider") or "").strip().lower()
        model = str(value.get("model") or "").strip()
        base_url = str(value.get("base_url") or "").strip().rstrip("/")
        api_key = str(value.get("api_key") or "")
        if provider not in {"openai", "openrouter", "anthropic", "ollama"}:
            raise ValueError("The selected model provider is not supported.")
        if not model:
            raise ValueError("A model is required.")
        if provider == "anthropic" and not base_url:
            base_url = "https://api.anthropic.com/v1"
        if not base_url:
            raise ValueError("The model provider base URL is required.")
        if provider != "ollama" and not api_key.strip():
            raise ValueError("The model provider API key is missing.")
        return cls(
            provider=provider, model=model, api_key=api_key, base_url=base_url,
            temperature=float(value.get("temperature", 0.7)), max_tokens=int(value.get("max_tokens", 4096)),
            top_p=float(value.get("top_p", 1.0)), frequency_penalty=float(value.get("frequency_penalty", 0.0)),
            presence_penalty=float(value.get("presence_penalty", 0.0)),
        )


class ModelClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return await asyncio.to_thread(self._complete, messages)

    def _complete(self, messages: list[dict[str, str]]) -> str:
        if self.settings.provider == "ollama":
            url = f"{self.settings.base_url}/api/chat"
            body = {"model": self.settings.model, "messages": messages, "stream": False,
                    "options": {"temperature": self.settings.temperature, "top_p": self.settings.top_p}}
            headers = {"Content-Type": "application/json"}
        elif self.settings.provider == "anthropic":
            url = f"{self.settings.base_url}/messages"
            system = "\n\n".join(
                str(message.get("content") or "")
                for message in messages
                if message.get("role") == "system"
            ).strip()
            provider_messages = [
                message for message in messages if message.get("role") != "system"
            ]
            body = {
                "model": self.settings.model,
                "messages": provider_messages,
                "max_tokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
                "top_p": self.settings.top_p,
            }
            if system:
                body["system"] = system
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.settings.api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            url = f"{self.settings.base_url}/chat/completions"
            body = {
                "model": self.settings.model, "messages": messages, "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens, "top_p": self.settings.top_p,
                "frequency_penalty": self.settings.frequency_penalty, "presence_penalty": self.settings.presence_penalty,
                "response_format": {"type": "json_object"},
            }
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.settings.api_key}"}
            if self.settings.provider == "openrouter":
                headers.update({"HTTP-Referer": "https://inquira.ai", "X-Title": "Inquira"})
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = _provider_error(exc.read())
            raise RuntimeError(f"The model provider rejected the request ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Could not reach the model provider. Check your network, proxy, and certificate settings.") from exc
        try:
            if self.settings.provider == "ollama":
                return str(payload["message"]["content"])
            if self.settings.provider == "anthropic":
                content = payload["content"]
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return str(block["text"])
                raise KeyError("text")
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("The model provider returned an invalid response.") from exc


def create_model_client(value: dict[str, Any]) -> ModelClient:
    return ModelClient(ModelSettings.from_dict(value))


def _provider_error(raw: bytes) -> str:
    try:
        payload = json.loads(raw)
        error = payload.get("error", payload)
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:500]
    except Exception:
        pass
    return "Check the provider configuration and model access."
