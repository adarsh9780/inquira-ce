from app.agent_v2.events import reset_agent_event_emitter, set_agent_event_emitter
from app.agent_v2.tools.search_schema import search_schema


def _sample_schema():
    return {
        "table_name": "orders",
        "columns": [
            {
                "name": "order_id",
                "dtype": "INTEGER",
                "description": "Unique identifier for each order",
                "aliases": ["order number", "order key"],
            },
            {
                "name": "gross_margin",
                "dtype": "DOUBLE",
                "description": "Profitability percentage for each order",
                "aliases": ["profitability", "margin pct"],
            },
            {
                "name": "customer_name",
                "dtype": "VARCHAR",
                "description": "Customer full name",
                "aliases": ["client", "buyer name"],
            },
        ],
    }


def test_search_schema_exact_name_match_returns_column():
    result = search_schema(
        schema=_sample_schema(),
        query="order_id",
        table_name="orders",
    )
    assert result["match_count"] == 1
    assert result["columns"][0]["name"] == "order_id"
    assert "aliases" not in result["columns"][0]


def test_search_schema_alias_match_returns_column():
    result = search_schema(
        schema=_sample_schema(),
        query="profitability",
        table_name="orders",
    )
    assert result["match_count"] == 1
    assert result["columns"][0]["name"] == "gross_margin"


def test_search_schema_description_substring_match_returns_column():
    result = search_schema(
        schema=_sample_schema(),
        query="full name",
        table_name="orders",
    )
    assert result["match_count"] == 1
    assert result["columns"][0]["name"] == "customer_name"


def test_search_schema_non_matching_query_returns_empty():
    result = search_schema(
        schema=_sample_schema(),
        query="nonexistent metric",
        table_name="orders",
    )
    assert result["match_count"] == 0
    assert result["columns"] == []


def test_search_schema_enforces_max_results():
    schema = {
        "table_name": "orders",
        "columns": [
            {
                "name": f"metric_{idx}",
                "dtype": "DOUBLE",
                "description": f"Metric value {idx}",
                "aliases": [f"metric alias {idx}"],
            }
            for idx in range(10)
        ],
    }
    result = search_schema(
        schema=schema,
        query="metric",
        table_name="orders",
        max_results=3,
    )
    assert result["match_count"] == 3
    assert len(result["columns"]) == 3


def test_search_schema_emits_tool_call_and_result_events():
    events: list[tuple[str, dict]] = []
    token = set_agent_event_emitter(lambda event, payload: events.append((event, payload)))
    try:
        result = search_schema(
            schema=_sample_schema(),
            query="order",
            table_name="orders",
        )
    finally:
        reset_agent_event_emitter(token)

    assert result["match_count"] >= 1
    assert events
    assert events[0][0] == "tool_call"
    assert events[0][1]["tool"] == "search_schema"
    assert events[-1][0] == "tool_result"
    assert events[-1][1]["status"] == "success"
