from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "app" / "legal" / "terms.md"


def test_terms_include_required_honest_risk_and_scope_clauses():
    text = TERMS.read_text(encoding="utf-8")

    assert "Commercial use is permitted." in text
    assert "provided \"AS IS\"" in text or "provided \"As Is\"" in text or "provided \"as is\"" in text.lower()
    assert "Generated code runs with your local user permissions" in text
    assert "You choose the LLM provider and are responsible for what you send." in text
    assert "No governing law or jurisdiction is designated in this version of the Terms." in text
    assert "your prompt/question" in text
    assert "schema context needed to generate code" in text
    assert "stored on your device" in text
