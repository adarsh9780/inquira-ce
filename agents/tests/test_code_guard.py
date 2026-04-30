from __future__ import annotations

from agent_v2.code_guard import guard_code


def test_guard_blocks_unbounded_select_all_fetchdf() -> None:
    result = guard_code(
        """
result_df = conn.sql("SELECT * FROM orders").fetchdf()
""".strip()
    )

    assert result.blocked is True
    assert result.should_retry is True
    assert "select *" in str(result.reason or "").lower()
    assert "bounded final result" in str(result.reason or "").lower()
