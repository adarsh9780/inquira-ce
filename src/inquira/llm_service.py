import os
from google import genai
from pathlib import Path
from dotenv import load_dotenv
from fastapi import HTTPException
from pydantic import BaseModel, Field


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
    """Service for interacting with Google Gemini LLM"""

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash"):
        """Initialize the LLM service with API key"""
        if api_key:
            self.api_key = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
        else:
            env_fp = Path(__file__).resolve().parents[2] / ".env"
            load_dotenv(env_fp)
            self.api_key = os.getenv("GOOGLE_API_KEY", "")

        self.model = model

        # Only initialize client if API key is available
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

        self.chat_client = None

    def create_chat_client(self, system_instruction: str = "", model: str = ""):
        if not self.client:
            raise HTTPException(
                status_code=503, detail="LLM service not available. API key not set."
            )

        if model:
            model = model
        else:
            model = self.model

        self.chat_client = self.client.chats.create(
            model=model,
            config=genai.types.GenerateContentConfig(
                temperature=0,
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=CodeOutput,
            ),
        )

        return self.chat_client

    def ask(self, user_query: str, structured_output_format):
        if not self.client:
            raise HTTPException(
                status_code=503, detail="LLM service not available. API key not set."
            )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_query,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": structured_output_format,
                },
            )
            return response.parsed
        except Exception:
            raise HTTPException(
                status_code=500, detail="Error while asking question from LLM"
            )

    def chat(self, message: str):
        """Send a message to the chat client and get response"""
        if not self.chat_client:
            raise HTTPException(
                status_code=400, detail="Chat client not initialized. Call create_chat_client first."
            )

        try:
            response = self.chat_client.send_message(message)
            return response.parsed
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error in chat conversation: {str(e)}"
            )
