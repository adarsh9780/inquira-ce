from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "maintenance" / "bump_versions.py"


def _load_module():
    spec = spec_from_file_location("bump_versions", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load bump_versions script module")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_validate_stable_version_accepts_release_and_v_prefix():
    mod = _load_module()
    assert mod.validate_stable_version("0.5.24") == "0.5.24"
    assert mod.validate_stable_version("v0.5.24") == "0.5.24"


def test_resolve_target_versions_allows_per_target_overrides():
    mod = _load_module()
    out = mod.resolve_target_versions(
        base_version="0.5.24",
        backend_version="0.5.25",
        tauri_version="0.5.26",
        frontend_version="0.5.27",
    )
    assert out == {
        "base": "0.5.24",
        "backend": "0.5.25",
        "tauri": "0.5.26",
        "frontend": "0.5.27",
    }


def test_run_updates_dry_run_reports_all_effective_versions():
    mod = _load_module()
    lines = mod.run_updates(base_version="0.6.0", dry_run=True)
    joined = "\n".join(lines)
    assert "base_version=0.6.0" in joined
    assert "backend_version=0.6.0" in joined
    assert "tauri_version=0.6.0" in joined
    assert "frontend_version=0.6.0" in joined
    assert "wheel_url=" not in joined


def test_stable_validation_rejects_prerelease_versions():
    mod = _load_module()
    try:
        mod.validate_stable_version("0.5.7a23")
        assert False, "Expected ValueError for prerelease format"
    except ValueError as exc:
        assert "Major.Minor.Patch" in str(exc)
    try:
        mod.validate_stable_version("0.5.7-alpha.23")
        assert False, "Expected ValueError for prerelease format"
    except ValueError as exc:
        assert "Major.Minor.Patch" in str(exc)


def test_build_desktop_asset_payload_uses_tauri_release_filenames():
    mod = _load_module()

    payload = mod.build_desktop_asset_payload(
        base_version="0.5.24",
        tauri_version="0.5.24",
    )

    assert payload == {
        "tag": "v0.5.24",
        "macos_asset_name": "Inquira_0.5.24_aarch64.dmg",
        "windows_asset_name": "Inquira_0.5.24_x64-setup.exe",
        "macos_url": (
            "https://github.com/adarsh9780/inquira-ce/releases/download/"
            "v0.5.24/Inquira_0.5.24_aarch64.dmg"
        ),
        "windows_url": (
            "https://github.com/adarsh9780/inquira-ce/releases/download/"
            "v0.5.24/Inquira_0.5.24_x64-setup.exe"
        ),
    }


def test_update_release_metadata_writes_versioned_json(
    monkeypatch, tmp_path: Path
):
    mod = _load_module()
    source = tmp_path / "release_metadata.md"
    source.write_text(
        "# Release v0.5.24\n\n- Fix workspace kernel release notes drift.\n",
        encoding="utf-8",
    )
    output = tmp_path / ".github" / "release" / "metadata.json"

    monkeypatch.setattr(mod, "RELEASE_METADATA_SOURCE", source)
    monkeypatch.setattr(mod, "RELEASE_METADATA_JSON", output)

    changed = mod.update_release_metadata("0.5.24")

    assert changed is True
    payload = output.read_text(encoding="utf-8")
    assert '"version": "0.5.24"' in payload
    assert '"tag": "v0.5.24"' in payload
    assert '"release_name": "Release v0.5.24"' in payload


def test_run_updates_reports_release_metadata_json_when_refreshed(
    monkeypatch, tmp_path: Path
):
    mod = _load_module()

    backend_pyproject = tmp_path / "backend" / "pyproject.toml"
    backend_pyproject.parent.mkdir(parents=True, exist_ok=True)
    backend_pyproject.write_text('version = "0.5.23"\n', encoding="utf-8")

    backend_main = tmp_path / "backend" / "app" / "main.py"
    backend_main.parent.mkdir(parents=True, exist_ok=True)
    backend_main.write_text('APP_VERSION = "0.5.23"\n', encoding="utf-8")

    tauri_cargo = tmp_path / "src-tauri" / "Cargo.toml"
    tauri_cargo.parent.mkdir(parents=True, exist_ok=True)
    tauri_cargo.write_text('version = "0.5.23"\n', encoding="utf-8")

    tauri_conf = tmp_path / "src-tauri" / "tauri.conf.json"
    tauri_conf.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_package = tmp_path / "frontend" / "package.json"
    frontend_package.parent.mkdir(parents=True, exist_ok=True)
    frontend_package.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_lock = tmp_path / "frontend" / "package-lock.json"
    frontend_lock.write_text(
        '{\n  "version": "0.5.23",\n  "packages": {\n    "": {\n      "version": "0.5.23"\n    }\n  }\n}\n',
        encoding="utf-8",
    )

    release_source = tmp_path / "release_metadata.md"
    release_source.write_text("# Release v0.5.24\n\n- Notes\n", encoding="utf-8")
    release_output = tmp_path / ".github" / "release" / "metadata.json"
    docs_download_page = tmp_path / "docs-site" / "src" / "pages" / "download.tsx"
    docs_download_page.parent.mkdir(parents=True, exist_ok=True)
    docs_download_page.write_text(
        "\n".join(
            [
                "const RELEASE_TAG =",
                "  'v0.5.23';",
                "const MACOS_ASSET_NAME =",
                "  'Inquira_0.5.23_aarch64.dmg';",
                "const WINDOWS_ASSET_NAME =",
                "  'Inquira_0.5.23_x64-setup.exe';",
                "const MACOS_FALLBACK_URL =",
                "  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_aarch64.dmg';",
                "const WINDOWS_FALLBACK_URL =",
                "  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_x64-setup.exe';",
                "",
            ]
        ),
        encoding="utf-8",
    )
    downloads_doc = tmp_path / "docs-site" / "docs" / "downloads.md"
    downloads_doc.parent.mkdir(parents=True, exist_ok=True)
    downloads_doc.write_text(
        "\n".join(
            [
                "- [macOS direct download](https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_aarch64.dmg)",
                "- [Windows direct download](https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_x64-setup.exe)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    install_doc = tmp_path / "docs-site" / "docs" / "install.md"
    install_doc.write_text(
        "\n".join(
            [
                "- [macOS (`.dmg`)](https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_aarch64.dmg)",
                "- [Windows (`.exe`)](https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_x64-setup.exe)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "BACKEND_PYPROJECT", backend_pyproject)
    monkeypatch.setattr(mod, "BACKEND_MAIN", backend_main)
    monkeypatch.setattr(mod, "TAURI_CARGO", tauri_cargo)
    monkeypatch.setattr(mod, "TAURI_CONF", tauri_conf)
    monkeypatch.setattr(mod, "FRONTEND_PACKAGE", frontend_package)
    monkeypatch.setattr(mod, "FRONTEND_LOCK", frontend_lock)
    monkeypatch.setattr(mod, "RELEASE_METADATA_SOURCE", release_source)
    monkeypatch.setattr(mod, "RELEASE_METADATA_JSON", release_output)
    monkeypatch.setattr(mod, "DOCS_DOWNLOAD_PAGE", docs_download_page)
    monkeypatch.setattr(mod, "DOCS_DOWNLOADS_DOC", downloads_doc)
    monkeypatch.setattr(mod, "DOCS_INSTALL_DOC", install_doc)

    results = mod.run_updates(base_version="0.5.24")

    assert any(
        ".github/release/metadata.json" in line for line in results
    )
    assert any("docs-site/src/pages/download.tsx" in line for line in results)
    assert any("docs-site/docs/downloads.md" in line for line in results)
    assert any("docs-site/docs/install.md" in line for line in results)
    assert "Inquira_0.5.24_aarch64.dmg" in docs_download_page.read_text(
        encoding="utf-8"
    )
    assert "Inquira_0.5.24_x64-setup.exe" in docs_download_page.read_text(
        encoding="utf-8"
    )


def test_run_updates_warns_for_missing_targets_instead_of_failing(
    monkeypatch, tmp_path: Path
):
    mod = _load_module()

    backend_pyproject = tmp_path / "backend" / "pyproject.toml"
    backend_pyproject.parent.mkdir(parents=True, exist_ok=True)
    backend_pyproject.write_text('version = "0.5.23"\n', encoding="utf-8")

    tauri_cargo = tmp_path / "src-tauri" / "Cargo.toml"
    tauri_cargo.parent.mkdir(parents=True, exist_ok=True)
    tauri_cargo.write_text('version = "0.5.23"\n', encoding="utf-8")

    tauri_conf = tmp_path / "src-tauri" / "tauri.conf.json"
    tauri_conf.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_package = tmp_path / "frontend" / "package.json"
    frontend_package.parent.mkdir(parents=True, exist_ok=True)
    frontend_package.write_text('{\n  "version": "0.5.23"\n}\n', encoding="utf-8")

    frontend_lock = tmp_path / "frontend" / "package-lock.json"
    frontend_lock.write_text(
        '{\n  "version": "0.5.23",\n  "packages": {\n    "": {\n      "version": "0.5.23"\n    }\n  }\n}\n',
        encoding="utf-8",
    )

    release_source = tmp_path / "release_metadata.md"
    release_source.write_text("# Release v0.5.24\n\n- Notes\n", encoding="utf-8")
    release_output = tmp_path / ".github" / "release" / "metadata.json"
    docs_download_page = tmp_path / "docs-site" / "src" / "pages" / "download.tsx"
    docs_download_page.parent.mkdir(parents=True, exist_ok=True)
    docs_download_page.write_text(
        "\n".join(
            [
                "const RELEASE_TAG =",
                "  'v0.5.23';",
                "const MACOS_ASSET_NAME =",
                "  'Inquira_0.5.23_aarch64.dmg';",
                "const WINDOWS_ASSET_NAME =",
                "  'Inquira_0.5.23_x64-setup.exe';",
                "const MACOS_FALLBACK_URL =",
                "  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_aarch64.dmg';",
                "const WINDOWS_FALLBACK_URL =",
                "  'https://github.com/adarsh9780/inquira-ce/releases/download/v0.5.23/Inquira_0.5.23_x64-setup.exe';",
                "",
            ]
        ),
        encoding="utf-8",
    )

    missing_backend_main = tmp_path / "backend" / "app" / "main.py"
    missing_downloads_doc = tmp_path / "docs-site" / "docs" / "downloads.md"
    missing_install_doc = tmp_path / "docs-site" / "docs" / "install.md"

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "BACKEND_PYPROJECT", backend_pyproject)
    monkeypatch.setattr(mod, "BACKEND_MAIN", missing_backend_main)
    monkeypatch.setattr(mod, "TAURI_CARGO", tauri_cargo)
    monkeypatch.setattr(mod, "TAURI_CONF", tauri_conf)
    monkeypatch.setattr(mod, "FRONTEND_PACKAGE", frontend_package)
    monkeypatch.setattr(mod, "FRONTEND_LOCK", frontend_lock)
    monkeypatch.setattr(mod, "RELEASE_METADATA_SOURCE", release_source)
    monkeypatch.setattr(mod, "RELEASE_METADATA_JSON", release_output)
    monkeypatch.setattr(mod, "DOCS_DOWNLOAD_PAGE", docs_download_page)
    monkeypatch.setattr(mod, "DOCS_DOWNLOADS_DOC", missing_downloads_doc)
    monkeypatch.setattr(mod, "DOCS_INSTALL_DOC", missing_install_doc)

    results = mod.run_updates(base_version="0.5.24")
    joined = "\n".join(results)

    assert "updated_files=" in joined
    assert "warning=missing_file:backend/app/main.py" in joined
    assert "warning=missing_file:docs-site/docs/downloads.md" in joined
    assert "warning=missing_file:docs-site/docs/install.md" in joined
    assert "Inquira_0.5.24_aarch64.dmg" in docs_download_page.read_text(
        encoding="utf-8"
    )
