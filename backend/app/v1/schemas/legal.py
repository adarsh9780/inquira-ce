"""Schemas for legal content APIs."""

from pydantic import BaseModel


class TermsResponse(BaseModel):
    """Rendered terms source payload."""

    markdown: str
    last_updated: str | None = None
