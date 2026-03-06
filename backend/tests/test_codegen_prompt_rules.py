from pathlib import Path


def _codegen_prompt_text() -> str:
    root = Path(__file__).resolve().parents[2]
    prompt_path = root / "backend" / "app" / "core" / "prompts" / "yaml" / "codegen_prompt.yaml"
    return prompt_path.read_text(encoding="utf-8")


def test_codegen_prompt_requires_descriptive_variable_names_with_stable_final_outputs():
    source = _codegen_prompt_text()
    assert "NEVER use generic output names such as `result`, `final_df`, `fig`, `data`, or `output`." in source
    assert "Intermediate/helper variables should be single-purpose and immutable within a snippet." in source
    assert "If data is modified (filter/sort/group/join/pivot/enrich), create a new intermediate variable name for that stage." in source
    assert "Final persisted output names should be stable across similar reruns so artifacts overwrite cleanly." in source
    assert "Reuse a final output name intentionally only when it represents the same business meaning; use a new final name when meaning changes." in source
    assert "`output_contract` is a list of objects like" in source
    assert "monthly_revenue_summary_df" in source
    assert "Do NOT serialize dataframe outputs via `.to_dict(...)`, `.to_json(...)`" in source
    assert "Keep final dataframe outputs as real dataframe objects" in source


def test_codegen_prompt_includes_plotly_industry_style_standards():
    source = _codegen_prompt_text()
    assert "## Plotly Standards (CRITICAL)" in source
    assert "Structure & clarity: order data logically" in source
    assert "Color: use 2-3 intentional colors" in source
    assert "Labels & typography: label title + axes + legends" in source
