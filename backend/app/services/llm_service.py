import os
import warnings
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .chat_model_factory import create_chat_model
from .llm_provider_catalog import normalize_llm_provider, provider_default_base_url, provider_requires_api_key
from .llm_runtime_config import load_llm_runtime_config, normalize_model_id


class CodeOutput(BaseModel):
    is_safe: bool = Field(description="if the query is safe return true else false")
    is_relevant: bool = Field(
        description="if the query is related to data analysis return true else false"
    )
    code: str = Field(
        description="if the query is safe and relevant, generate a Python code which can analyse the data"
    )
    explanation: str = Field(
        description="the reasoning behind the code or if there is no code, then whatever is model output should be stored in here"
    )


class LLMService:
    """Service for interacting with OpenAI-compatible LLM providers."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "google/gemini-2.5-flash",
        provider: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
    ):
        """Initialize LLM service with API key and OpenAI-compatible base URL."""
        runtime = load_llm_runtime_config()
        resolved_provider = normalize_llm_provider(provider or runtime.provider)
        if api_key:
            self.api_key = api_key
        else:
            backend_env = Path(__file__).resolve().parents[2] / ".env"
            repo_root_env = Path(__file__).resolve().parents[3] / ".env"
            # Load both so local dev can keep .env at repo root or backend root.
            load_dotenv(backend_env)
            load_dotenv(repo_root_env)
            self.api_key = self._load_provider_api_key(resolved_provider)

        self.model = normalize_model_id(model) or runtime.default_model
        if base_url is not None and str(base_url).strip():
            self.base_url = str(base_url).strip()
        elif resolved_provider == "openrouter":
            self.base_url = runtime.base_url
        else:
            self.base_url = provider_default_base_url(resolved_provider)
        self.provider = resolved_provider
        self.requires_api_key = provider_requires_api_key(resolved_provider)
        self.temperature = float(temperature)
        self.top_p = top_p
        self.top_k = top_k
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.default_max_tokens = int(max_tokens) if max_tokens is not None else runtime.default_max_tokens
        self.client: Any | None
        self.chat_client: Any | None

        self.client = None
        if self.api_key or not self.requires_api_key:
            self.client = create_chat_model(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                max_retries=0,  # Fail fast instead of hanging the UI with automatic retries
                timeout=60.0,
            )

        self.chat_client = None

    @staticmethod
    def _load_provider_api_key(provider: str) -> str:
        provider_name = str(provider or "").strip().lower()
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama": "OLLAMA_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_var = env_vars.get(provider_name, "OPENROUTER_API_KEY")
        return os.getenv(env_var, "").strip()

    @staticmethod
    def _structured_output_methods(client: Any) -> tuple[str | None, ...]:
        provider = str(getattr(client, "_inquira_provider", "") or "").strip().lower()
        if provider == "ollama":
            return ("json_schema", "function_calling", "json_mode")
        return (None,)

    @staticmethod
    def _is_recoverable_structured_output_error(exc: Exception) -> bool:
        message = str(exc or "").strip().lower()
        if not message:
            return False
        markers = (
            "expected value at line",
            "expecting value: line 1 column 1",
            "jsondecodeerror",
            "json error injected into sse stream",
            "outputparserexception",
            "invalid json output",
            "unsupported response_format type",
            "not support json schema",
            "structured outputs not supported",
        )
        return any(marker in message for marker in markers)

    @staticmethod
    def _bind_structured_output(client: Any, schema: Any, method: str | None) -> Any:
        if method is None:
            return client.with_structured_output(schema)
        try:
            return client.with_structured_output(schema, method=method, include_raw=False)
        except TypeError:
            return client.with_structured_output(schema)

    def create_chat_client(self, system_instruction: str = "", model: str = ""):
        if not self.client:
            raise HTTPException(
                status_code=503, detail="LLM service not available. API key not set."
            )

        selected_model = normalize_model_id((model or self.model).strip() or self.model)

        model_client = create_chat_model(
            provider=self.provider,
            model=selected_model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            max_tokens=self.default_max_tokens,
            max_retries=0,  # Fail fast
            timeout=60.0,
        )
        last_exc: Exception | None = None
        self.chat_client = None
        for method in self._structured_output_methods(model_client):
            try:
                self.chat_client = self._bind_structured_output(model_client, CodeOutput, method)
                break
            except Exception as exc:
                last_exc = exc
                if not self._is_recoverable_structured_output_error(exc):
                    raise
        if self.chat_client is None and last_exc is not None:
            raise last_exc
        self.chat_system_instruction = system_instruction or ""

        return self.chat_client

    def ask(self, user_query: str, structured_output_format, max_tokens: int | None = None):
        if not self.client:
            raise HTTPException(
                status_code=503, detail="LLM service not available. API key not set."
            )

        try:
            effective_max_tokens = max_tokens or self.default_max_tokens
            client = create_chat_model(
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                max_tokens=effective_max_tokens,
                max_retries=0,
                timeout=60.0,
            )
            if structured_output_format is str:
                response = client.invoke(user_query)
                return getattr(response, "content", str(response))

            # LangChain/OpenAI structured-output currently triggers a noisy
            # pydantic serializer warning for schema model classes in some versions.
            # Suppress only that known warning path so schema regeneration logs stay clean.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"^Pydantic serializer warnings:",
                    category=UserWarning,
                )
                last_exc: Exception | None = None
                methods = self._structured_output_methods(client)
                for idx, method in enumerate(methods):
                    try:
                        structured = self._bind_structured_output(client, structured_output_format, method)
                        return structured.invoke(user_query)
                    except Exception as exc:
                        last_exc = exc
                        if idx >= len(methods) - 1:
                            raise
                        if not self._is_recoverable_structured_output_error(exc):
                            raise
                if last_exc is not None:
                    raise last_exc
                raise RuntimeError("Structured output invocation failed without an error.")
        except HTTPException:
            raise
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            if isinstance(status_code, int) and 400 <= status_code <= 599:
                raise HTTPException(status_code=status_code, detail=str(e))
            raise HTTPException(
                status_code=500, detail=f"Error while asking question from LLM: {str(e)}"
            )

    def chat(self, message: str):
        """Send a message to the chat client and get response"""
        if not self.chat_client:
            raise HTTPException(
                status_code=400, detail="Chat client not initialized. Call create_chat_client first."
            )

        try:
            messages: list[BaseMessage] = []
            if getattr(self, "chat_system_instruction", ""):
                messages.append(SystemMessage(content=self.chat_system_instruction))
            messages.append(HumanMessage(content=message))
            return self.chat_client.invoke(messages)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error in chat conversation: {str(e)}"
            )
