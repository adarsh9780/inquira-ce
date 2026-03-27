from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAURI_LIB = ROOT / "src-tauri" / "src" / "lib.rs"


def test_windows_startup_uses_platform_uv_binary_name_only():
    text = TAURI_LIB.read_text(encoding="utf-8")

    assert "fn bundled_uv_candidates(resource_dir: &Path) -> Vec<PathBuf>" in text
    assert "let bundled_names = vec![uv_binary_file_name()];" in text
    assert 'let bundled_roots = vec!["bundled-tools", "src-tauri/bundled-tools"];' in text
    assert 'format!("{bundled_root}/{candidate_name}")' in text
    assert "candidates.extend(bundled_uv_candidates(resource_dir));" in text
