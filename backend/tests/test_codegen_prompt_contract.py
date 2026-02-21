from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "app" / "core" / "prompts" / "yaml"


def test_codegen_prompt_uses_browser_query_bridge_contract():
    prompt = (PROMPTS_DIR / "codegen_prompt.yaml").read_text(encoding="utf-8")
    assert "await query(" in prompt
    assert "table_name = " in prompt
    assert "NEVER import `duckdb`" in prompt


def test_codegen_prompt_disallows_python_duckdb_backend_patterns():
    prompt = (PROMPTS_DIR / "codegen_prompt.yaml").read_text(encoding="utf-8")
    assert "con = ibis.duckdb.connect()" not in prompt
    assert "t = con.read_csv(" not in prompt
    assert "Use `con.read_csv" not in prompt
    assert "To finalize a calculation, call `.execute()` on the Ibis expression" not in prompt
