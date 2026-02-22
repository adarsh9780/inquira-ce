"""Cursor encoding/decoding utilities for paginated turn APIs."""

from __future__ import annotations

import base64
import json
from datetime import datetime


def encode_cursor(created_at: datetime, turn_id: str) -> str:
    """Encode a pagination cursor from timestamp and turn id."""
    raw = json.dumps({"created_at": created_at.isoformat(), "turn_id": turn_id})
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str | None) -> tuple[datetime | None, str | None]:
    """Decode cursor into timestamp and turn id.

    Returns (None, None) when cursor is absent or invalid.
    """
    if not cursor:
        return None, None
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        payload = json.loads(decoded)
        return datetime.fromisoformat(payload["created_at"]), str(payload["turn_id"])
    except Exception:
        return None, None
