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
