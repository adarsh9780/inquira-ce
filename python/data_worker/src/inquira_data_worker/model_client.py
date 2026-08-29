"""Small async clients for OpenAI-compatible providers and Ollama."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import ssl
import urllib.error
import urllib.parse
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
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer"
    api_version: str = ""
    organization: str = ""
    project: str = ""
    proxy_mode: str = "system"
    proxy_url: str = ""
    no_proxy: str = ""
    ca_bundle_path: str = ""
    client_certificate_path: str = ""
    client_key_path: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ModelSettings":
        provider = str(value.get("provider") or "").strip().lower()
        model = str(value.get("model") or "").strip()
        base_url = str(value.get("base_url") or "").strip().rstrip("/")
        api_key = str(value.get("api_key") or "")
        if provider not in {"openai", "openrouter", "anthropic", "openai-compatible", "ollama"}:
            raise ValueError("The selected model provider is not supported.")
        if not model:
            raise ValueError("A model is required.")
        if provider == "anthropic" and not base_url:
            base_url = "https://api.anthropic.com/v1"
        if not base_url:
            raise ValueError("The model provider base URL is required.")
        if provider != "ollama" and not api_key.strip():
            raise ValueError("The model provider API key is missing.")
        api_key_prefix = value.get("api_key_prefix")
        if api_key_prefix is None and provider in {"openai", "openrouter", "openai-compatible"}:
            api_key_prefix = "Bearer"
        return cls(
            provider=provider, model=model, api_key=api_key, base_url=base_url,
            temperature=float(value.get("temperature", 0.7)), max_tokens=int(value.get("max_tokens", 4096)),
            top_p=float(value.get("top_p", 1.0)), frequency_penalty=float(value.get("frequency_penalty", 0.0)),
            presence_penalty=float(value.get("presence_penalty", 0.0)),
            api_key_header=str(value.get("api_key_header") or "Authorization").strip(),
            api_key_prefix=str(api_key_prefix or "").strip(),
            api_version=str(value.get("api_version") or "").strip(),
            organization=str(value.get("organization") or "").strip(),
            project=str(value.get("project") or "").strip(),
            proxy_mode=str(value.get("proxy_mode") or "system").strip().lower(),
            proxy_url=str(value.get("proxy_url") or "").strip(),
            no_proxy=str(value.get("no_proxy") or "").strip(),
            ca_bundle_path=str(value.get("ca_bundle_path") or "").strip(),
            client_certificate_path=str(value.get("client_certificate_path") or "").strip(),
            client_key_path=str(value.get("client_key_path") or "").strip(),
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
            url = self._provider_url("/chat/completions")
            body = {
                "model": self.settings.model, "messages": messages, "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens, "top_p": self.settings.top_p,
                "frequency_penalty": self.settings.frequency_penalty, "presence_penalty": self.settings.presence_penalty,
                "response_format": {"type": "json_object"},
            }
            credential = self.settings.api_key
            if self.settings.api_key_prefix:
                credential = f"{self.settings.api_key_prefix} {credential}"
            headers = {"Content-Type": "application/json", self.settings.api_key_header: credential}
            if self.settings.organization:
                headers["OpenAI-Organization"] = self.settings.organization
            if self.settings.project:
                headers["OpenAI-Project"] = self.settings.project
            if self.settings.provider == "openrouter":
                headers.update({"HTTP-Referer": "https://inquira.ai", "X-Title": "Inquira"})
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            open_request = self._request_opener(url)
            with open_request(request, timeout=120) as response:
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

    def _request_opener(self, request_url: str) -> Any:
        uses_default_network = (
            self.settings.proxy_mode == "system"
            and not self.settings.no_proxy
            and not self.settings.ca_bundle_path
            and not self.settings.client_certificate_path
        )
        if uses_default_network:
            return urllib.request.urlopen
        return self._build_opener(request_url).open

    def _provider_url(self, path: str) -> str:
        parsed = urllib.parse.urlsplit(self.settings.base_url)
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        if self.settings.api_version:
            query["api-version"] = self.settings.api_version
        return urllib.parse.urlunsplit((
            parsed.scheme,
            parsed.netloc,
            f"{parsed.path.rstrip('/')}{path}",
            urllib.parse.urlencode(query),
            parsed.fragment,
        ))

    def _build_opener(self, request_url: str) -> urllib.request.OpenerDirector:
        handlers: list[Any] = []
        request_host = urllib.parse.urlsplit(request_url).hostname or ""
        if self.settings.proxy_mode == "direct" or _host_matches_no_proxy(request_host, self.settings.no_proxy):
            handlers.append(urllib.request.ProxyHandler({}))
        elif self.settings.proxy_mode == "custom":
            handlers.append(urllib.request.ProxyHandler({
                "http": self.settings.proxy_url,
                "https": self.settings.proxy_url,
            }))

        if self.settings.ca_bundle_path or self.settings.client_certificate_path:
            context = ssl.create_default_context(cafile=self.settings.ca_bundle_path or None)
            if self.settings.client_certificate_path:
                context.load_cert_chain(
                    certfile=self.settings.client_certificate_path,
                    keyfile=self.settings.client_key_path,
                )
            handlers.append(urllib.request.HTTPSHandler(context=context))
        return urllib.request.build_opener(*handlers)


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


def _host_matches_no_proxy(host: str, raw_patterns: str) -> bool:
    normalized_host = host.strip().lower()
    for raw_pattern in raw_patterns.split(","):
        pattern = raw_pattern.strip().lower()
        if not pattern:
            continue
        if pattern == "*":
            return True
        try:
            if ipaddress.ip_address(normalized_host) in ipaddress.ip_network(pattern, strict=False):
                return True
        except ValueError:
            pass
        pattern = pattern.removeprefix("*.").removeprefix(".").split(":", 1)[0]
        if normalized_host == pattern or normalized_host.endswith(f".{pattern}"):
            return True
    return False
