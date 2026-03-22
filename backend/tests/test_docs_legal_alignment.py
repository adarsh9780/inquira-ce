from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs-site" / "docs"


def test_auth_strategy_describes_current_supabase_flow_not_legacy_password_flow():
    text = (DOCS / "auth-strategy.md").read_text(encoding="utf-8")

    assert "Supabase-backed bearer auth" in text
    assert "Google sign-in" in text
    assert "old local username/password flow" in text
    assert "the current desktop app still gates workspace access behind sign-in" in text
    assert "v1 auth routes issue and clear a `session_token` cookie" not in text
    assert "repository implementation is still a placeholder that raises runtime errors" not in text


def test_privacy_and_terms_do_not_overclaim_billing_or_multi_provider_support():
    privacy = (DOCS / "privacy-policy.md").read_text(encoding="utf-8")
    terms = (DOCS / "terms-of-service.md").read_text(encoding="utf-8")

    assert "does not currently operate its own hosted billing or subscription portal" in privacy
    assert "the current sign-in ui is centered around google login" in privacy.lower()
    assert "hosted account portal" in terms
    assert "These Terms do not grant rights beyond the applicable software license." in terms
    assert "Google, Microsoft, GitHub, and Supabase" not in terms
