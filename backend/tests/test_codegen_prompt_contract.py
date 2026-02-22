from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "app" / "core" / "prompts" / "yaml"


def test_codegen_prompt_uses_duckdb_narwhals_contract():
    prompt = (PROMPTS_DIR / "codegen_prompt.yaml").read_text(encoding="utf-8")
    assert "import narwhals as nw" in prompt
    assert "import duckdb" in prompt
    assert "duckdb.connect()" in prompt
    assert "con.read_csv(" in prompt
    assert "nw.from_native(duckdb_rel)" in prompt


def test_codegen_prompt_removes_pyodide_contract():
    prompt = (PROMPTS_DIR / "codegen_prompt.yaml").read_text(encoding="utf-8")
    assert "await query(" in prompt  # The prompt explicitly forbids it now
    assert "NEVER use or generate" in prompt
    assert "Pyodide" not in prompt
    assert "DuckDB-WASM" not in prompt
