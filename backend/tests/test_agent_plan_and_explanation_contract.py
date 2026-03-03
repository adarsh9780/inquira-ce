from pathlib import Path
import inspect

from app.agent.graph import InquiraAgent


def test_sanitize_plan_text_removes_code_blocks_and_code_like_lines():
    raw_plan = """
Plan Objective:
Find top players by total runs.

Steps:
1. Build batting team mapping
   Columns: Innings, Bat First, Bat Second, Batter Runs
   Action: map each batter row to the right team.

```python
team_df = df.groupby("Batter").sum()
```

batting_totals = team_df.sort_values("Batter Runs", ascending=False)
"""

    cleaned = InquiraAgent._sanitize_plan_text(raw_plan)

    assert "```" not in cleaned
    assert "team_df =" not in cleaned
    assert "batting_totals =" not in cleaned
    assert "Columns: Innings, Bat First, Bat Second, Batter Runs" in cleaned


def test_create_plan_prompt_requires_plain_english_steps_without_code():
    prompt_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "core"
        / "prompts"
        / "yaml"
        / "create_plan_prompt.yaml"
    )
    prompt_text = prompt_path.read_text(encoding="utf-8")

    assert "Do NOT include Python, SQL, pseudocode" in prompt_text
    assert "one analytical step at a time" in prompt_text
    assert "Columns:" in prompt_text
    assert "shown directly to end users" in prompt_text
    assert "Use markdown formatting with numbered steps and bullet points" in prompt_text


def test_explain_code_prompt_requires_sectioned_code_walkthrough():
    source = inspect.getsource(InquiraAgent.explain_code)

    assert "Break the long code into 3 to 6 logical pieces" in source
    assert "Next step" in source
    assert "_invoke_text_chain_with_streaming(" in source
    assert 'node_name="explain_code"' in source


def test_explanation_fallback_chunker_produces_multiple_sections():
    code = """
import duckdb
import pandas as pd

table_name = "matches"
raw_df = conn.sql(f'SELECT * FROM "{table_name}"').df()

summary_df = (
    raw_df.groupby("team", as_index=False)
    .agg({"runs": "sum"})
)

top_df = summary_df.sort_values("runs", ascending=False).head(10)
chart_fig = None
"""
    sections = InquiraAgent._normalize_explanation_sections([], code)
    assert len(sections) >= 3
    assert all(section.get("code") for section in sections)
    assert all(section.get("explanation") for section in sections)


def test_compose_sectioned_explanation_contains_multiple_code_blocks():
    markdown = InquiraAgent._compose_sectioned_explanation(
        overview="This script prepares and summarizes team runs.",
        sections=[
            {
                "title": "Load data",
                "language": "python",
                "code": "import duckdb\nraw_df = conn.sql('SELECT 1').df()",
                "explanation": "This block loads data into a table-like object.",
            },
            {
                "title": "Aggregate",
                "language": "python",
                "code": "summary_df = raw_df.groupby('team').sum()",
                "explanation": "This block totals runs by team.",
            },
            {
                "title": "Sort results",
                "language": "python",
                "code": "top_df = summary_df.sort_values('runs', ascending=False)",
                "explanation": "This block ranks teams from highest to lowest runs.",
            },
        ],
        next_step="Review the top teams in the table output.",
        follow_up_question="Do you want a chart version as well?",
    )
    assert markdown.count("```python") >= 3
    assert "### Next step" in markdown
    assert markdown.strip().endswith("?")
