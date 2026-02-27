from app.agent.code_guard import guard_code
from app.agent.graph import InquiraAgent, State


def test_code_guard_allows_conn_backed_duckdb_execution():
    code = """
import duckdb
import narwhals as nw
duckdb_rel = conn.sql('SELECT * FROM "sales" LIMIT 100')
res = nw.from_native(duckdb_rel)
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


def test_code_guard_blocks_plotly_with_narwhals_wrapper():
    code = """
import narwhals as nw
import plotly.express as px
df = nw.from_native(conn.sql("SELECT 1 AS value").pl())
fig = px.bar(df, x="value", y="value")
fig
"""
    result = guard_code(code, table_name="events")
    assert result.blocked is True
    assert result.should_retry is True
    assert "Plotly requires a native/pandas dataframe" in (result.reason or "")


def test_code_guard_blocks_file_loader_patterns():
    code = """
import pandas as pd
df = pd.read_excel("source.xlsx")
df
"""
    result = guard_code(code, table_name="events")
    assert result.blocked is True
    assert result.should_retry is True
    assert "Source-file loaders are not allowed" in (result.reason or "")
