from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / "src-tauri" / "src" / "lib.rs"


def test_windows_startup_accepts_bundled_uv_without_exe_suffix():
    text = TAURI_LIB.read_text(encoding="utf-8")

    assert "fn bundled_uv_candidates(resource_dir: &Path) -> Vec<PathBuf>" in text
    assert 'let bundled_names = vec![uv_binary_file_name(), "uv"];' in text
    assert 'format!("bundled-tools/{candidate_name}")' in text
    assert "candidates.extend(bundled_uv_candidates(resource_dir));" in text
