"""Structured errors returned across the worker boundary."""

from __future__ import annotations


class AdapterError(Exception):
    """An expected, user-actionable adapter failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
