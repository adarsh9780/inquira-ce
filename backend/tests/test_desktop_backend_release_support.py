from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / 'src-tauri' / 'src' / 'lib.rs'
SUPABASE_SQL = ROOT / 'backend' / 'sql' / 'supabase' / 'account_plans.sql'


def test_desktop_runtime_starts_backend_from_python_venv():
    text = TAURI_LIB.read_text(encoding='utf-8')

    assert 'fn start_backend(' in text
    assert 'Command::new(&python_bin)' in text
    assert '.args(["-m", "app.main"])' in text
    assert 'bundled_backend_bin' not in text
    assert 'NUITKA_PYTHONPATH' not in text


def test_supabase_plan_sql_defines_free_pro_enterprise_contract():
    text = SUPABASE_SQL.read_text(encoding='utf-8')

    assert 'create table if not exists public.account_plans' in text
    assert "('FREE', 'PRO', 'ENTERPRISE')" in text
    assert 'alter table public.account_plans enable row level security;' in text
    assert 'users can read their own plan' in text
