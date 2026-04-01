from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / "src-tauri" / "src" / "lib.rs"


def test_desktop_python_bootstrap_skips_dev_dependencies():
    text = TAURI_LIB.read_text(encoding="utf-8")

    assert 'cmd.args([' in text
    assert '"sync"' in text
    assert '"--no-dev"' in text
    assert '"--project"' in text
    assert 'project_dir.to_str().unwrap()' in text
