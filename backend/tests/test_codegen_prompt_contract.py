from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "app" / "core" / "prompts" / "yaml"


def test_codegen_prompt_uses_duckdb_narwhals_contract():
    prompt = (PROMPTS_DIR / "codegen_prompt.yaml").read_text(encoding="utf-8")
    assert "import narwhals as nw" in prompt
    assert "import duckdb" in prompt
    assert "duckdb.connect()" in prompt
    assert 'conn.sql(f"SELECT * FROM {table_name} LIMIT 100")' in prompt
    assert "nw.from_native(duckdb_rel)" in prompt
