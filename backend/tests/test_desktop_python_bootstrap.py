from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / "src-tauri" / "src" / "lib.rs"


def test_desktop_python_bootstrap_skips_dev_dependencies():
    text = TAURI_LIB.read_text(encoding="utf-8")

    assert "fn build_uv_sync_args(" in text
    assert "python_spec: Option<&str>" in text
    assert '"sync".to_string()' in text
    assert '"--no-dev".to_string()' in text
    assert '"--project".to_string()' in text
    assert 'project_dir.to_string_lossy().to_string()' in text
    assert '"--python".to_string()' in text
