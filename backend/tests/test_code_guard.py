from app.agent.code_guard import build_bridge_fallback_code, guard_code
from app.agent.graph import InquiraAgent, State


def test_code_guard_rewrites_conn_sql_fetchdf_to_bridge_query():
    code = """
import duckdb
conn = duckdb.connect()
df = conn.sql("SELECT 1 AS a").fetchdf()
df
"""
    result = guard_code(code, table_name="sales", allow_fallback=False)
    assert result.blocked is False
    assert "await query(" in result.code
    assert "duckdb.connect(" not in result.code
    assert "import duckdb" not in result.code


def test_code_guard_rewrites_to_fallback_when_no_bridge_query_present():
    code = """
import pandas as pd
x = 1 + 1
x
"""
    strict_result = guard_code(code, table_name="events", allow_fallback=False)
    assert strict_result.blocked is True
    assert strict_result.should_retry is True

    fallback_result = guard_code(code, table_name="events", allow_fallback=True)
    assert fallback_result.blocked is False
    assert 'table_name = "events"' in fallback_result.code
    assert "await query(" in fallback_result.code


def test_code_guard_converts_ibis_duckdb_setup_to_bridge_fallback():
    code = """
import ibis
con = ibis.duckdb.connect()
t = con.read_parquet("x.parquet")
t
"""
    result = guard_code(code, table_name="events", allow_fallback=True)
    assert result.blocked is False
    # Forbidden setup is removed and replaced by bridge-safe fallback.
    assert "await query(" in result.code


def test_code_guard_fallback_builder_uses_table_name():
    code = build_bridge_fallback_code("orders")
    assert 'table_name = "orders"' in code
    assert "await query(" in code


def test_code_guard_node_requests_retry_then_fallback():
    agent = InquiraAgent()
    state = State(messages=[], code="x = 1", table_name="events")

    first = agent.code_guard(state, {})
    assert first["guard_status"] == "retry"
    assert first["code_guard_retries"] == 1
    assert first["code_guard_feedback"]

    retry_state = state.model_copy(
        update={
            "code_guard_retries": 1,
            "code_guard_feedback": first["code_guard_feedback"],
            "code": "x = 1",
        }
    )
    second = agent.code_guard(retry_state, {})
    assert second["guard_status"] == "ok"
    assert "await query(" in second["code"]
