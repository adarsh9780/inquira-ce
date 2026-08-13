"""Validated, renderer-independent chart specifications compiled to Plotly JSON."""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Any, Iterable, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator


CHART_SPEC_SCHEMA = "inquira.chart/v1"
CHART_SPEC_MEDIA_TYPE = "application/vnd.inquira.chart.v1+json"


class ChartSpecError(ValueError):
    """An invalid chart specification or incompatible dataframe."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ChartMark(StrEnum):
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    SCATTER = "scatter"
    PIE = "pie"
    DONUT = "donut"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"
    BOX = "box"
    VIOLIN = "violin"


class FieldType(StrEnum):
    QUANTITATIVE = "quantitative"
    NOMINAL = "nominal"
    ORDINAL = "ordinal"
    TEMPORAL = "temporal"


class SortDirection(StrEnum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class ChartDataReference(BaseModel):
    """A dataframe artifact produced by the same analysis."""

    model_config = ConfigDict(extra="forbid")

    logical_name: str = Field(min_length=1, max_length=128)
    artifact_id: str | None = Field(default=None, min_length=1, max_length=256)


class FieldEncoding(BaseModel):
    """A constrained semantic mapping from a dataframe column to a visual channel."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=256)
    type: FieldType
    title: str | None = Field(default=None, max_length=256)
    sort: SortDirection | None = None


class ChartEncoding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: FieldEncoding | None = None
    y: FieldEncoding | None = None
    color: FieldEncoding | None = None
    size: FieldEncoding | None = None
    theta: FieldEncoding | None = None
    text: FieldEncoding | None = None


class ChartOptions(BaseModel):
    """A deliberately small set of presentation choices the agent may control."""

    model_config = ConfigDict(extra="forbid")

    orientation: Literal["vertical", "horizontal"] = "vertical"
    stacking: Literal["grouped", "stacked", "normalized"] = "grouped"
    show_markers: bool = True


class ChartSpec(BaseModel):
    """The canonical chart artifact authored by the agent."""

    model_config = ConfigDict(extra="forbid")

    schema_: Literal[CHART_SPEC_SCHEMA] = Field(
        default=CHART_SPEC_SCHEMA,
        alias="schema",
        serialization_alias="schema",
    )
    data: ChartDataReference
    mark: ChartMark
    encoding: ChartEncoding
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=1000)
    options: ChartOptions = Field(default_factory=ChartOptions)

    @model_validator(mode="after")
    def validate_required_channels(self) -> ChartSpec:
        available = {
            name
            for name in ("x", "y", "color", "size", "theta", "text")
            if getattr(self.encoding, name) is not None
        }
        required_by_mark = {
            ChartMark.BAR: {"x", "y"},
            ChartMark.LINE: {"x", "y"},
            ChartMark.AREA: {"x", "y"},
            ChartMark.SCATTER: {"x", "y"},
            ChartMark.PIE: {"theta", "color"},
            ChartMark.DONUT: {"theta", "color"},
            ChartMark.HEATMAP: {"x", "y", "color"},
            ChartMark.HISTOGRAM: {"x"},
            ChartMark.BOX: {"x", "y"},
            ChartMark.VIOLIN: {"x", "y"},
        }
        missing = required_by_mark[self.mark] - available
        if missing:
            channels = ", ".join(sorted(missing))
            raise ValueError(f"{self.mark.value} charts require: {channels}")
        if self.mark in {ChartMark.PIE, ChartMark.DONUT} and self.options.orientation != "vertical":
            raise ValueError("Pie and donut charts do not support horizontal orientation")
        if self.mark not in {ChartMark.BAR, ChartMark.AREA} and self.options.stacking != "grouped":
            raise ValueError("Stacking is only supported for bar and area charts")
        return self


def chart_spec_json_schema() -> dict[str, Any]:
    """Return the JSON schema used by agent structured output and API validation."""

    return ChartSpec.model_json_schema(by_alias=True)


def _field(enc: FieldEncoding | None) -> str:
    if enc is None:  # pragma: no cover - guarded by ChartSpec validation
        raise ChartSpecError("chart_channel_missing", "A required chart channel is missing.")
    return enc.field


def _columns(spec: ChartSpec) -> set[str]:
    return {
        channel.field
        for channel in (
            spec.encoding.x,
            spec.encoding.y,
            spec.encoding.color,
            spec.encoding.size,
            spec.encoding.theta,
            spec.encoding.text,
        )
        if channel is not None
    }


def _validate_records(spec: ChartSpec, records: list[Mapping[str, Any]]) -> None:
    if not records:
        raise ChartSpecError("chart_data_empty", "The selected dataframe has no rows to chart.")
    present = {str(key) for record in records for key in record}
    missing = sorted(_columns(spec) - present)
    if missing:
        raise ChartSpecError(
            "chart_field_missing",
            "The dataframe does not contain chart field(s): " + ", ".join(missing),
        )


def _sorted_records(
    records: list[Mapping[str, Any]],
    encoding: FieldEncoding | None,
) -> list[Mapping[str, Any]]:
    if encoding is None or encoding.sort is None:
        return records
    reverse = encoding.sort == SortDirection.DESCENDING
    try:
        return sorted(
            records,
            key=lambda record: (record.get(encoding.field) is None, record.get(encoding.field)),
            reverse=reverse,
        )
    except TypeError:
        return sorted(
            records,
            key=lambda record: str(record.get(encoding.field) or ""),
            reverse=reverse,
        )


def _grouped(records: list[Mapping[str, Any]], field: str | None) -> list[tuple[str | None, list[Mapping[str, Any]]]]:
    if not field:
        return [(None, records)]
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(field, ""))].append(record)
    return list(groups.items())


def _axis_title(encoding: FieldEncoding | None) -> str | None:
    if encoding is None:
        return None
    return encoding.title or encoding.field


def _cartesian_trace(
    spec: ChartSpec,
    records: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    x_field, y_field = _field(spec.encoding.x), _field(spec.encoding.y)
    color_field = spec.encoding.color.field if spec.encoding.color else None
    traces: list[dict[str, Any]] = []
    for group_name, group_rows in _grouped(records, color_field):
        trace: dict[str, Any] = {
            "type": "bar" if spec.mark == ChartMark.BAR else "scatter",
            "x": [row.get(x_field) for row in group_rows],
            "y": [row.get(y_field) for row in group_rows],
        }
        if group_name is not None:
            trace["name"] = group_name
        if spec.mark == ChartMark.LINE:
            trace["mode"] = "lines+markers" if spec.options.show_markers else "lines"
        elif spec.mark == ChartMark.AREA:
            trace.update(
                mode="lines",
                stackgroup="inquira" if spec.options.stacking != "grouped" else None,
                groupnorm="percent" if spec.options.stacking == "normalized" else None,
                fill="tozeroy" if spec.options.stacking == "grouped" else None,
            )
            trace = {key: value for key, value in trace.items() if value is not None}
        elif spec.mark == ChartMark.SCATTER:
            trace["mode"] = "markers"
            if spec.encoding.size:
                trace["marker"] = {
                    "size": [row.get(spec.encoding.size.field) for row in group_rows],
                    "sizemode": "area",
                }
        elif spec.mark == ChartMark.BAR and spec.options.orientation == "horizontal":
            trace["x"], trace["y"] = trace["y"], trace["x"]
            trace["orientation"] = "h"
        traces.append(trace)
    return traces


def _distribution_trace(
    spec: ChartSpec,
    records: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    x_field, y_field = _field(spec.encoding.x), _field(spec.encoding.y)
    color_field = spec.encoding.color.field if spec.encoding.color else None
    traces = []
    for group_name, group_rows in _grouped(records, color_field):
        trace: dict[str, Any] = {
            "type": spec.mark.value,
            "x": [row.get(x_field) for row in group_rows],
            "y": [row.get(y_field) for row in group_rows],
            "boxpoints" if spec.mark == ChartMark.BOX else "points": "outliers",
        }
        if group_name is not None:
            trace["name"] = group_name
        traces.append(trace)
    return traces


def _heatmap_trace(spec: ChartSpec, records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    x_field = _field(spec.encoding.x)
    y_field = _field(spec.encoding.y)
    color_field = _field(spec.encoding.color)
    x_values = list(dict.fromkeys(row.get(x_field) for row in records))
    y_values = list(dict.fromkeys(row.get(y_field) for row in records))
    cells: dict[tuple[Any, Any], Any] = {}
    for row in records:
        key = (row.get(x_field), row.get(y_field))
        if key in cells:
            raise ChartSpecError(
                "chart_heatmap_duplicate_cell",
                "Heatmap data must have one row for each x/y combination.",
            )
        cells[key] = row.get(color_field)
    return [{
        "type": "heatmap",
        "x": x_values,
        "y": y_values,
        "z": [[cells.get((x_value, y_value)) for x_value in x_values] for y_value in y_values],
        "colorbar": {"title": _axis_title(spec.encoding.color)},
    }]


def compile_chart_spec(
    value: ChartSpec | Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate an Inquira chart spec and deterministically compile Plotly JSON."""

    spec = value if isinstance(value, ChartSpec) else ChartSpec.model_validate(value)
    rows = [dict(record) for record in records]
    _validate_records(spec, rows)
    sort_encoding = spec.encoding.y if spec.encoding.y and spec.encoding.y.sort else spec.encoding.x
    rows = _sorted_records(rows, sort_encoding)

    if spec.mark in {ChartMark.BAR, ChartMark.LINE, ChartMark.AREA, ChartMark.SCATTER}:
        traces = _cartesian_trace(spec, rows)
    elif spec.mark in {ChartMark.BOX, ChartMark.VIOLIN}:
        traces = _distribution_trace(spec, rows)
    elif spec.mark == ChartMark.HISTOGRAM:
        x_field = _field(spec.encoding.x)
        traces = [{"type": "histogram", "x": [row.get(x_field) for row in rows]}]
    elif spec.mark in {ChartMark.PIE, ChartMark.DONUT}:
        traces = [{
            "type": "pie",
            "labels": [row.get(_field(spec.encoding.color)) for row in rows],
            "values": [row.get(_field(spec.encoding.theta)) for row in rows],
            "hole": 0.5 if spec.mark == ChartMark.DONUT else 0,
        }]
    elif spec.mark == ChartMark.HEATMAP:
        traces = _heatmap_trace(spec, rows)
    else:  # pragma: no cover - exhaustive enum guard
        raise ChartSpecError("chart_mark_unsupported", f"Unsupported chart mark: {spec.mark}")

    horizontal = spec.mark == ChartMark.BAR and spec.options.orientation == "horizontal"
    layout: dict[str, Any] = {
        "title": {"text": spec.title},
        "xaxis": {"title": {"text": _axis_title(spec.encoding.y if horizontal else spec.encoding.x)}},
        "yaxis": {"title": {"text": _axis_title(spec.encoding.x if horizontal else spec.encoding.y)}},
    }
    if spec.mark == ChartMark.BAR:
        layout["barmode"] = {
            "grouped": "group",
            "stacked": "stack",
            "normalized": "stack",
        }[spec.options.stacking]
        if spec.options.stacking == "normalized":
            layout["barnorm"] = "percent"

    return {
        "data": traces,
        "layout": layout,
        "config": {"responsive": True, "displaylogo": False},
    }
