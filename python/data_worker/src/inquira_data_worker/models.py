"""Language-neutral adapter request and response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    nullable: bool = True


@dataclass(frozen=True)
class SourceObject:
    id: str
    name: str
    kind: str
    columns: list[Column] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterRequest:
    source_path: str
    source_object_id: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Discovery:
    adapter_kind: str
    source_path: str
    fingerprint: str
    objects: list[SourceObject]


@dataclass(frozen=True)
class Preview:
    columns: list[Column]
    rows: list[dict[str, Any]]
    truncated: bool


@dataclass(frozen=True)
class MaterializeRequest:
    source_path: str
    target_dir: str
    selected_object_ids: list[str]
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterializedOutput:
    source_object_id: str
    name: str
    relative_path: str
    format: str
    columns: list[Column]
    row_count: int
    byte_size: int


@dataclass(frozen=True)
class Materialization:
    fingerprint: str
    outputs: list[MaterializedOutput]
