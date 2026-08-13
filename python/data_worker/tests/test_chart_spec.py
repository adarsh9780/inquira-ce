from __future__ import annotations

import pytest
from pydantic import ValidationError

from inquira_data_worker.chart_spec import (
    CHART_SPEC_SCHEMA,
    ChartSpec,
    ChartSpecError,
    chart_spec_json_schema,
    compile_chart_spec,
)


def _spec(mark: str = "bar") -> dict:
    return {
        "schema": CHART_SPEC_SCHEMA,
        "data": {"logical_name": "top_regions"},
        "mark": mark,
        "encoding": {
            "x": {"field": "region", "type": "nominal", "title": "Region"},
            "y": {
                "field": "revenue",
                "type": "quantitative",
                "title": "Revenue",
                "sort": "descending",
            },
        },
        "title": "Revenue by region",
    }


def test_chart_spec_is_strict_versioned_and_requires_mark_channels() -> None:
    parsed = ChartSpec.model_validate(_spec())
    assert parsed.model_dump(by_alias=True)["schema"] == CHART_SPEC_SCHEMA

    extra = _spec()
    extra["layout"] = {"paper_bgcolor": "red"}
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ChartSpec.model_validate(extra)

    invalid_pie = _spec("pie")
    with pytest.raises(ValidationError, match="pie charts require: color, theta"):
        ChartSpec.model_validate(invalid_pie)

    schema = chart_spec_json_schema()
    assert schema["properties"]["schema"]["const"] == CHART_SPEC_SCHEMA
    assert schema["additionalProperties"] is False


def test_bar_spec_compiles_grouped_sorted_plotly_json_without_style_control() -> None:
    spec = _spec()
    spec["encoding"]["color"] = {"field": "segment", "type": "nominal"}
    compiled = compile_chart_spec(
        spec,
        [
            {"region": "North", "revenue": 10, "segment": "Consumer"},
            {"region": "South", "revenue": 30, "segment": "Enterprise"},
            {"region": "West", "revenue": 20, "segment": "Consumer"},
        ],
    )

    assert compiled["data"] == [
        {
            "type": "bar",
            "x": ["South"],
            "y": [30],
            "name": "Enterprise",
        },
        {
            "type": "bar",
            "x": ["West", "North"],
            "y": [20, 10],
            "name": "Consumer",
        },
    ]
    assert compiled["layout"] == {
        "title": {"text": "Revenue by region"},
        "xaxis": {"title": {"text": "Region"}},
        "yaxis": {"title": {"text": "Revenue"}},
        "barmode": "group",
    }
    assert compiled["config"] == {"responsive": True, "displaylogo": False}


def test_chart_compiler_rejects_missing_fields_and_empty_data() -> None:
    with pytest.raises(ChartSpecError) as missing:
        compile_chart_spec(_spec(), [{"region": "North"}])
    assert missing.value.code == "chart_field_missing"
    assert "revenue" in missing.value.message

    with pytest.raises(ChartSpecError) as empty:
        compile_chart_spec(_spec(), [])
    assert empty.value.code == "chart_data_empty"


def test_donut_and_heatmap_specs_compile_common_analytical_charts() -> None:
    donut = {
        "schema": CHART_SPEC_SCHEMA,
        "data": {"logical_name": "share"},
        "mark": "donut",
        "encoding": {
            "theta": {"field": "amount", "type": "quantitative"},
            "color": {"field": "category", "type": "nominal"},
        },
        "title": "Category share",
    }
    assert compile_chart_spec(
        donut,
        [{"category": "A", "amount": 60}, {"category": "B", "amount": 40}],
    )["data"] == [{
        "type": "pie",
        "labels": ["A", "B"],
        "values": [60, 40],
        "hole": 0.5,
    }]

    heatmap = {
        "schema": CHART_SPEC_SCHEMA,
        "data": {"logical_name": "matrix"},
        "mark": "heatmap",
        "encoding": {
            "x": {"field": "month", "type": "ordinal"},
            "y": {"field": "region", "type": "nominal"},
            "color": {"field": "revenue", "type": "quantitative", "title": "Revenue"},
        },
        "title": "Revenue matrix",
    }
    chart = compile_chart_spec(
        heatmap,
        [
            {"month": "Jan", "region": "North", "revenue": 10},
            {"month": "Feb", "region": "North", "revenue": 20},
            {"month": "Jan", "region": "South", "revenue": 30},
        ],
    )
    assert chart["data"][0]["z"] == [[10, 20], [30, None]]

    with pytest.raises(ChartSpecError) as duplicate:
        compile_chart_spec(
            heatmap,
            [
                {"month": "Jan", "region": "North", "revenue": 10},
                {"month": "Jan", "region": "North", "revenue": 20},
            ],
        )
    assert duplicate.value.code == "chart_heatmap_duplicate_cell"
