"""API v1 legal content endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from ..schemas.legal import TermsResponse

router = APIRouter(prefix="/legal", tags=["V1 Legal"])

_TERMS_FILE = Path(__file__).resolve().parents[2] / "legal" / "terms.md"


def _extract_last_updated(markdown: str) -> str | None:
    for raw_line in str(markdown or "").splitlines():
        line = str(raw_line or "").strip()
        if line.lower().startswith("last updated:"):
            value = line.split(":", 1)[-1].strip()
            return value or None
    return None


@router.get("/terms", response_model=TermsResponse)
async def get_terms() -> TermsResponse:
    markdown = _TERMS_FILE.read_text(encoding="utf-8")
    return TermsResponse(
        markdown=markdown,
        last_updated=_extract_last_updated(markdown),
    )
