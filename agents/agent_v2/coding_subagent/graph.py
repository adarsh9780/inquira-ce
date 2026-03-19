from __future__ import annotations


def generate_code_plan(question: str, table_name: str) -> str:
    q = str(question or "").strip()
    t = str(table_name or "data").strip() or "data"
    return f"Use table `{t}` to answer: {q}. Return a dataframe named result_df."
