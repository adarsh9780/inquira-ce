import os
import warnings
from pathlib import Path
from typing import Any, cast
from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel, Field, SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

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

    def __init__(self, api_key: str = "", model: str = "google/gemini-2.5-flash"):
        """Initialize LLM service with API key and OpenAI-compatible base URL."""
        runtime = load_llm_runtime_config()
        if api_key:
            self.api_key = api_key
        else:
            backend_env = Path(__file__).resolve().parents[2] / ".env"
            repo_root_env = Path(__file__).resolve().parents[3] / ".env"
            # Load both so local dev can keep .env at repo root or backend root.
            load_dotenv(backend_env)
            load_dotenv(repo_root_env)
            self.api_key = os.getenv("OPENROUTER_API_KEY", "")

        self.model = normalize_model_id(model) or runtime.default_model
        self.base_url = runtime.base_url
        self.default_max_tokens = runtime.default_max_tokens
        self.client: Any | None
        self.chat_client: Any | None

        self.client = None
        if self.api_key:
            self.client = ChatOpenAI(
                model=self.model,
                api_key=SecretStr(self.api_key),
                base_url=self.base_url,
                temperature=0,
                max_retries=0,  # Fail fast instead of hanging the UI with automatic retries
                timeout=60.0,
            )

        self.chat_client = None

    def create_chat_client(self, system_instruction: str = "", model: str = ""):
        if not self.client:
            raise HTTPException(
                status_code=503, detail="LLM service not available. API key not set."
            )

        selected_model = normalize_model_id((model or self.model).strip() or self.model)

        model_client = ChatOpenAI(
            model=selected_model,
            api_key=SecretStr(self.api_key),
            base_url=self.base_url,
            temperature=0,
            max_retries=0,  # Fail fast
            timeout=60.0,
        )
        bounded_model_client = cast(Any, model_client.bind(max_tokens=self.default_max_tokens))
        self.chat_client = bounded_model_client.with_structured_output(CodeOutput)
        self.chat_system_instruction = system_instruction or ""

        return self.chat_client

    def ask(self, user_query: str, structured_output_format, max_tokens: int | None = None):
        if not self.client:
            raise HTTPException(
                status_code=503, detail="LLM service not available. API key not set."
            )

        try:
            effective_max_tokens = max_tokens or self.default_max_tokens
            client = self.client.bind(max_tokens=effective_max_tokens)
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
                chain = client.with_structured_output(structured_output_format)
                return chain.invoke(user_query)
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
