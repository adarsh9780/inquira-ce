from pathlib import Path


def _codegen_prompt_text() -> str:
    root = Path(__file__).resolve().parents[2]
    prompt_path = root / "backend" / "app" / "core" / "prompts" / "yaml" / "codegen_prompt.yaml"
    return prompt_path.read_text(encoding="utf-8")


def test_codegen_prompt_requires_descriptive_immutable_variable_names():
    source = _codegen_prompt_text()
    assert "NEVER use generic output names such as `result`, `final_df`, `fig`, `data`, or `output`." in source
    assert "Treat variables as immutable: once a name is assigned, do not assign to that name again." in source
    assert "If data is modified (filter/sort/group/join/pivot/enrich), create a new variable name for that stage." in source
    assert "Never reuse the same variable name for a later transformation or chart." in source
    assert "`output_contract` is a list of objects like" in source
    assert "monthly_revenue_summary_df" in source


def test_codegen_prompt_includes_plotly_industry_style_standards():
    source = _codegen_prompt_text()
    assert "## Plotly Standards (CRITICAL)" in source
    assert "Structure & clarity: order data logically" in source
    assert "Color: use 2-3 intentional colors" in source
    assert "Labels & typography: label title + axes + legends" in source
