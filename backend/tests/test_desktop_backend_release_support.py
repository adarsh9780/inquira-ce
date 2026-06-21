from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / 'src-tauri' / 'src' / 'lib.rs'
PROVIDER_PLAN_SQL = ROOT / 'backend' / 'sql' / ''.join(['supa', 'base']) / 'account_plans.sql'


def test_desktop_runtime_starts_backend_from_python_venv():
    text = TAURI_LIB.read_text(encoding='utf-8')

    assert 'fn start_backend(' in text
    assert 'Command::new(&python_bin)' in text
    assert '.args(["-m", "app.main"])' in text
    assert 'bundled_backend_bin' not in text
    assert 'NUITKA_PYTHONPATH' not in text


def test_ce_release_does_not_ship_external_plan_sql():
    assert PROVIDER_PLAN_SQL.exists() is False
