from __future__ import annotations

import pytest

from inquira_data_worker.agent_guard import UnsafeCodeError, validate_analysis_code


@pytest.mark.parametrize("code", [
    "result = conn.execute(\"COPY sales TO '/tmp/leak.csv'\").df()",
    "result = conn.sql(\"SELECT * FROM read_csv_auto('/etc/passwd')\").df()",
    "query = 'SELECT 1'\nresult = conn.execute(query).df()",
    "result = getattr(__builtins__, 'open')('/tmp/leak', 'w')",
])
def test_guard_rejects_sql_file_access_dynamic_sql_and_reflection(code: str) -> None:
    with pytest.raises(UnsafeCodeError):
        validate_analysis_code(code)


@pytest.mark.parametrize("code", [
    "result = conn.execute('SELECT SUM(amount) AS total FROM sales').df()",
    "import pandas as pd\nresult = pd.DataFrame({'total': [42]})",
    "import plotly.express as px\nresult = px.bar(pd.DataFrame({'x': [1], 'y': [2]}), x='x', y='y')",
])
def test_guard_allows_in_memory_analysis(code: str) -> None:
    validate_analysis_code(code)
