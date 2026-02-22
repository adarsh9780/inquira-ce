from app.agent.code_guard import guard_code
from app.agent.graph import InquiraAgent, State


def test_code_guard_allows_duckdb_and_narwhals_execution():
    code = """
import duckdb
import narwhals as nw
conn = duckdb.connect()
df = conn.read_csv("data.csv")
res = nw.from_native(df)
res
"""
    result = guard_code(code, table_name="sales")
    assert result.blocked is False
    assert result.code == code.strip()


def test_code_guard_blocks_empty_code():
    code = "   \n  "
    result = guard_code(code, table_name="events")
    assert result.blocked is True
    assert result.should_retry is True
    assert "Empty code" in result.reason
    assert result.code == ""


def test_code_guard_node_preserves_valid_code():
    agent = InquiraAgent()
    code = "import duckdb\ncon = duckdb.connect()"
    state = State(messages=[], code=code, table_name="events")

    result = agent.code_guard(state, {})
    assert result["guard_status"] == "ok"
    assert result["code"] == code


def test_code_guard_node_uses_current_code_when_code_is_empty():
    agent = InquiraAgent()
    legacy_code = "df = await query('SELECT 1')\ndf"
    state = State(
        messages=[],
        code="",
        current_code=legacy_code,
        table_name="events",
        code_guard_retries=0,
    )

    result = agent.code_guard(state, {})
    assert result["guard_status"] == "retry"
    assert result["code_guard_retries"] == 1
    assert "Legacy `await query(...)` bridge detected." in result["code_guard_feedback"]


def test_code_guard_blocks_legacy_await_query_bridge_without_rewriting():
    code = """
table_name = "deliveries"
_guard_df = await query(f"SELECT * FROM {table_name} LIMIT 100")
_guard_df
"""
    result = guard_code(code, table_name="deliveries")

    assert result.blocked is True
    assert result.should_retry is True
    assert "await query(" in result.code
    assert "Legacy `await query(...)` bridge detected." in (result.reason or "")


def test_code_guard_node_fails_closed_after_retry_exhaustion():
    agent = InquiraAgent()
    legacy_code = "df = await query('SELECT 1')\ndf"
    state = State(
        messages=[],
        code=legacy_code,
        current_code=legacy_code,
        table_name="events",
        code_guard_retries=2,
    )

    result = agent.code_guard(state, {})
    assert result["guard_status"] == "failed"
    assert result["code"] == ""
    assert result["current_code"] == ""
    assert "Legacy `await query(...)` bridge detected." in result["code_guard_feedback"]
