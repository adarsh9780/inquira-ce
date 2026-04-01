from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / 'src-tauri' / 'src' / 'lib.rs'
SUPABASE_SQL = ROOT / 'backend' / 'sql' / 'supabase' / 'account_plans.sql'


def test_desktop_runtime_can_prefer_bundled_compiled_backend():
    text = TAURI_LIB.read_text(encoding='utf-8')

    assert 'fn bundled_backend_binary_file_name()' in text
    assert 'fn bundled_backend_candidates(resource_dir: &Path) -> Vec<PathBuf>' in text
    assert 'find_bundled_backend_binary(&resource_dir)' in text
    assert 'if bundled_backend_bin.is_some() {' in text
    assert 'if let Some(compiled_backend_bin) = bundled_backend_bin {' in text
    assert '.parent()' in text


def test_supabase_plan_sql_defines_free_pro_enterprise_contract():
    text = SUPABASE_SQL.read_text(encoding='utf-8')

    assert 'create table if not exists public.account_plans' in text
    assert "('FREE', 'PRO', 'ENTERPRISE')" in text
    assert 'alter table public.account_plans enable row level security;' in text
    assert 'users can read their own plan' in text
