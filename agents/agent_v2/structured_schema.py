"""JSON Schema helpers for OpenAI-compatible structured outputs."""

from __future__ import annotations

from typing import Any


def _strip_defaults(schema: Any) -> None:
    if isinstance(schema, dict):
        schema.pop("default", None)
        for value in schema.values():
            _strip_defaults(value)
    elif isinstance(schema, list):
        for item in schema:
            _strip_defaults(item)


def openai_strict_json_schema(schema: dict[str, Any]) -> None:
    """Keep Pydantic validation ergonomic while emitting OpenAI strict schemas.

    OpenAI's Responses API requires object schemas to list every property in
    `required`, even when a value is optional and represented as nullable.
    Pydantic defaults make fields optional in JSON Schema, so we normalize the
    emitted schema here without changing runtime model defaults.
    """

    properties = schema.get("properties")
    if isinstance(properties, dict):
        schema["required"] = list(properties.keys())
    _strip_defaults(schema)
