"""Shared v1 schemas."""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
