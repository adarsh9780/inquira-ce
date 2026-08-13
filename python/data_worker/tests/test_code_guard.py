from inquira_data_worker.agent_v2.code_guard import guard_code


def test_code_guard_blocks_agent_authored_plotly_rendering() -> None:
    for code in (
        "import plotly.express as px\nchart = px.bar(summary, x='region', y='sales')",
        "from plotly import graph_objects as go\nchart = go.Figure()",
        "export_figure({'data': []})",
    ):
        result = guard_code(code)
        assert result.blocked is True
        assert "chart_spec" in str(result.reason)


def test_code_guard_allows_bounded_dataframe_preparation() -> None:
    result = guard_code(
        "summary = conn.sql('SELECT region, SUM(sales) AS sales FROM sales GROUP BY region LIMIT 20').df()"
    )
    assert result.blocked is False
