from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "app" / "legal" / "terms.md"


def test_terms_include_required_honest_risk_and_scope_clauses():
    text = TERMS.read_text(encoding="utf-8")

    assert "These Terms do not grant rights beyond the applicable software license." in text
    assert "provided \"AS IS\"" in text or "provided \"As Is\"" in text or "provided \"as is\"" in text.lower()
    assert "Generated Python, manually entered Python, and terminal commands run locally" in text
    assert "Execution is not sandboxed." in text
    assert "policy checks reduce some risks but are not a security boundary" in text
    assert "You choose the AI provider and are responsible for what you send." in text
    assert "No governing law or jurisdiction is designated in this version of the Terms." in text
    assert "your prompt/question" in text or "your prompt or question" in text
    assert "schema context needed to generate code" in text
    assert "stored on your device" in text or "primarily stored on your device" in text
    assert "without account sign-in" in text
    assert "-backed bearer auth" not in text
    assert "login" not in text
