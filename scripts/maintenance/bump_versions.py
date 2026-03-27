#!/usr/bin/env python3
"""Bump project versions from a single source of truth.

Single source:
- VERSION (stable SemVer core, e.g. 0.5.0)

Targets:
- backend/pyproject.toml
- backend/app/main.py APP_VERSION
- src-tauri/Cargo.toml package.version
- src-tauri/tauri.conf.json version
- frontend/package.json version
- frontend/package-lock.json top-level version + packages[""].version
- .github/release/metadata.json version/tag/name/body when release_metadata.md exists
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "VERSION"
BACKEND_PYPROJECT = ROOT / "backend" / "pyproject.toml"
BACKEND_MAIN = ROOT / "backend" / "app" / "main.py"
TAURI_CARGO = ROOT / "src-tauri" / "Cargo.toml"
TAURI_CONF = ROOT / "src-tauri" / "tauri.conf.json"
FRONTEND_PACKAGE = ROOT / "frontend" / "package.json"
FRONTEND_LOCK = ROOT / "frontend" / "package-lock.json"
RELEASE_METADATA_SOURCE = ROOT / "release_metadata.md"
RELEASE_METADATA_JSON = ROOT / ".github" / "release" / "metadata.json"
DOCS_DOWNLOAD_PAGE = ROOT / "docs-site" / "src" / "pages" / "download.tsx"
DOCS_DOWNLOADS_DOC = ROOT / "docs-site" / "docs" / "downloads.md"
DOCS_INSTALL_DOC = ROOT / "docs-site" / "docs" / "install.md"
STABLE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def warning_for_missing_path(path: Path) -> str:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        relative = path
    return f"warning=missing_file:{relative}"


def normalize_version_input(version: str) -> str:
    """Accept optional leading tag marker and normalize to base version input."""
    v = version.strip()
    if v.startswith("v"):
        return v[1:]
    return v


def validate_stable_version(version: str, *, field: str = "version") -> str:
    """Validate and normalize a stable version in Major.Minor.Patch format."""
    v = normalize_version_input(version)
    if not STABLE_VERSION_RE.fullmatch(v):
        raise ValueError(
            f"Unsupported {field} format: {version!r}. Use stable Major.Minor.Patch only, e.g. 0.5.24"
        )
    return v


def read_version(cli_version: str | None) -> str:
    if cli_version:
        return normalize_version_input(cli_version)
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def resolve_target_versions(
    base_version: str,
    backend_version: str | None = None,
    tauri_version: str | None = None,
    frontend_version: str | None = None,
) -> dict[str, str]:
    effective_base = validate_stable_version(base_version, field="base version")
    effective_backend = validate_stable_version(
        backend_version or effective_base, field="backend version"
    )
    effective_tauri = validate_stable_version(
        tauri_version or effective_backend, field="tauri version"
    )
    effective_frontend = validate_stable_version(
        frontend_version or effective_tauri, field="frontend version"
    )

    return {
        "base": effective_base,
        "backend": effective_backend,
        "tauri": effective_tauri,
        "frontend": effective_frontend,
    }


def parse_release_metadata_markdown(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines()

    title_index = None
    for idx, raw in enumerate(lines):
        if raw.strip():
            title_index = idx
            break

    if title_index is None:
        raise ValueError("release_metadata.md is empty; provide a title and body")

    raw_title = lines[title_index].strip()
    if raw_title.startswith("#"):
        raw_title = raw_title.lstrip("#").strip()
    if not raw_title:
        raise ValueError("release_metadata.md title line is empty")

    body_lines = lines[title_index + 1 :]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    body = "\n".join(body_lines).strip()
    return raw_title, body


def build_release_metadata_payload(version: str, title: str, body: str) -> dict[str, str]:
    tag = version if version.startswith("v") else f"v{version}"
    return {
        "version": version.removeprefix("v"),
        "tag": tag,
        "release_name": title,
        "release_body": body,
    }


def build_desktop_asset_payload(
    base_version: str,
    tauri_version: str,
) -> dict[str, str]:
    tag = base_version if base_version.startswith("v") else f"v{base_version}"
    macos_asset = f"Inquira_{tauri_version}_aarch64.dmg"
    windows_asset = f"Inquira_{tauri_version}_x64-setup.exe"
    base_url = f"https://github.com/adarsh9780/inquira-ce/releases/download/{tag}"
    return {
        "tag": tag,
        "macos_asset_name": macos_asset,
        "windows_asset_name": windows_asset,
        "macos_url": f"{base_url}/{macos_asset}",
        "windows_url": f"{base_url}/{windows_asset}",
    }


def update_release_metadata(version: str) -> bool:
    if not RELEASE_METADATA_SOURCE.exists():
        return False

    title, body = parse_release_metadata_markdown(
        RELEASE_METADATA_SOURCE.read_text(encoding="utf-8")
    )
    payload = build_release_metadata_payload(version=version, title=title, body=body)
    updated = json.dumps(payload, indent=2) + "\n"
    current = (
        RELEASE_METADATA_JSON.read_text(encoding="utf-8")
        if RELEASE_METADATA_JSON.exists()
        else None
    )
    if current == updated:
        return False
    RELEASE_METADATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    RELEASE_METADATA_JSON.write_text(updated, encoding="utf-8")
    return True


def replace_text(path: Path, pattern: str, replacement: str) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def update_backend_pyproject(version: str) -> bool:
    return replace_text(
        BACKEND_PYPROJECT,
        r'^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
    )


def update_backend_main(version: str) -> bool:
    return replace_text(
        BACKEND_MAIN,
        r'^APP_VERSION\s*=\s*"[^"]+"',
        f'APP_VERSION = "{version}"',
    )


def update_tauri_cargo(tauri_version: str) -> bool:
    return replace_text(
        TAURI_CARGO,
        r'^version\s*=\s*"[^"]+"',
        f'version = "{tauri_version}"',
    )


def update_tauri_conf(tauri_version: str) -> bool:
    payload = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    if payload.get("version") == tauri_version:
        return False
    payload["version"] = tauri_version
    TAURI_CONF.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True


def update_frontend_package(frontend_version: str) -> bool:
    payload = json.loads(FRONTEND_PACKAGE.read_text(encoding="utf-8"))
    if payload.get("version") == frontend_version:
        return False
    payload["version"] = frontend_version
    FRONTEND_PACKAGE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True


def update_frontend_lock(frontend_version: str) -> bool:
    payload = json.loads(FRONTEND_LOCK.read_text(encoding="utf-8"))
    changed = False
    if payload.get("version") != frontend_version:
        payload["version"] = frontend_version
        changed = True

    packages = payload.get("packages")
    if isinstance(packages, dict):
        root_pkg = packages.get("")
        if isinstance(root_pkg, dict) and root_pkg.get("version") != frontend_version:
            root_pkg["version"] = frontend_version
            changed = True

    if changed:
        FRONTEND_LOCK.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return changed


def update_docs_download_links(base_version: str, tauri_version: str) -> tuple[list[str], list[str]]:
    payload = build_desktop_asset_payload(base_version=base_version, tauri_version=tauri_version)
    changed: list[str] = []
    warnings: list[str] = []

    if DOCS_DOWNLOAD_PAGE.exists():
        page = DOCS_DOWNLOAD_PAGE.read_text(encoding="utf-8")
        updated_page = page
        replacements = {
            "RELEASE_TAG": payload["tag"],
            "MACOS_ASSET_NAME": payload["macos_asset_name"],
            "WINDOWS_ASSET_NAME": payload["windows_asset_name"],
            "MACOS_FALLBACK_URL": payload["macos_url"],
            "WINDOWS_FALLBACK_URL": payload["windows_url"],
        }
        for key, value in replacements.items():
            updated_page = re.sub(
                rf"const {key} =\n\s+'[^']+';",
                f"const {key} =\n  '{value}';",
                updated_page,
            )
        if updated_page != page:
            DOCS_DOWNLOAD_PAGE.write_text(updated_page, encoding="utf-8")
            changed.append(str(DOCS_DOWNLOAD_PAGE.relative_to(ROOT)))
    else:
        warnings.append(warning_for_missing_path(DOCS_DOWNLOAD_PAGE))

    if DOCS_DOWNLOADS_DOC.exists():
        downloads_doc = DOCS_DOWNLOADS_DOC.read_text(encoding="utf-8")
        updated_downloads_doc = re.sub(
            r"- \[macOS direct download\]\([^)]+\)\n- \[Windows direct download\]\([^)]+\)",
            (
                f"- [macOS direct download]({payload['macos_url']})\n"
                f"- [Windows direct download]({payload['windows_url']})"
            ),
            downloads_doc,
        )
        if updated_downloads_doc != downloads_doc:
            DOCS_DOWNLOADS_DOC.write_text(updated_downloads_doc, encoding="utf-8")
            changed.append(str(DOCS_DOWNLOADS_DOC.relative_to(ROOT)))
    else:
        warnings.append(warning_for_missing_path(DOCS_DOWNLOADS_DOC))

    if DOCS_INSTALL_DOC.exists():
        install_doc = DOCS_INSTALL_DOC.read_text(encoding="utf-8")
        updated_install_doc = re.sub(
            r"- \[macOS \(`\.dmg`\)\]\([^)]+\)\n- \[Windows \(`\.exe`\)\]\([^)]+\)",
            (
                f"- [macOS (`.dmg`)]({payload['macos_url']})\n"
                f"- [Windows (`.exe`)]({payload['windows_url']})"
            ),
            install_doc,
        )
        if updated_install_doc != install_doc:
            DOCS_INSTALL_DOC.write_text(updated_install_doc, encoding="utf-8")
            changed.append(str(DOCS_INSTALL_DOC.relative_to(ROOT)))
    else:
        warnings.append(warning_for_missing_path(DOCS_INSTALL_DOC))

    return changed, warnings


def run_updates(
    base_version: str,
    dry_run: bool = False,
    backend_version: str | None = None,
    tauri_version: str | None = None,
    frontend_version: str | None = None,
) -> list[str]:
    versions = resolve_target_versions(
        base_version=base_version,
        backend_version=backend_version,
        tauri_version=tauri_version,
        frontend_version=frontend_version,
    )
    results: list[str] = [
        f"base_version={versions['base']}",
        f"backend_version={versions['backend']}",
        f"tauri_version={versions['tauri']}",
        f"frontend_version={versions['frontend']}",
    ]
    if dry_run:
        return results

    changed: list[str] = []
    warnings: list[str] = []

    if BACKEND_PYPROJECT.exists():
        if update_backend_pyproject(versions["backend"]):
            changed.append("backend/pyproject.toml")
    else:
        warnings.append(warning_for_missing_path(BACKEND_PYPROJECT))

    if BACKEND_MAIN.exists():
        if update_backend_main(versions["backend"]):
            changed.append("backend/app/main.py")
    else:
        warnings.append(warning_for_missing_path(BACKEND_MAIN))

    if TAURI_CARGO.exists():
        if update_tauri_cargo(versions["tauri"]):
            changed.append("src-tauri/Cargo.toml")
    else:
        warnings.append(warning_for_missing_path(TAURI_CARGO))

    if TAURI_CONF.exists():
        if update_tauri_conf(versions["tauri"]):
            changed.append("src-tauri/tauri.conf.json")
    else:
        warnings.append(warning_for_missing_path(TAURI_CONF))

    if FRONTEND_PACKAGE.exists():
        if update_frontend_package(versions["frontend"]):
            changed.append("frontend/package.json")
    else:
        warnings.append(warning_for_missing_path(FRONTEND_PACKAGE))

    if FRONTEND_LOCK.exists():
        if update_frontend_lock(versions["frontend"]):
            changed.append("frontend/package-lock.json")
    else:
        warnings.append(warning_for_missing_path(FRONTEND_LOCK))

    if update_release_metadata(versions["base"]):
        changed.append(".github/release/metadata.json")

    docs_changed, docs_warnings = update_docs_download_links(
        base_version=versions["base"],
        tauri_version=versions["tauri"],
    )
    changed.extend(docs_changed)
    warnings.extend(docs_warnings)

    if changed:
        results.append("updated_files=" + ",".join(changed))
    else:
        results.append("updated_files=<none>")
    results.extend(warnings)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump project versions from VERSION file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/maintenance/bump_versions.py --help\n"
            "  uv run python scripts/maintenance/bump_versions.py --version 0.5.24 --dry-run\n"
            "  uv run python scripts/maintenance/bump_versions.py --version 0.5.24 --write-version-file\n"
            "  uv run python scripts/maintenance/bump_versions.py \\\n"
            "    --version 0.5.24 \\\n"
            "    --backend-version 0.5.24 \\\n"
            "    --tauri-version 0.5.24 \\\n"
            "    --frontend-version 0.5.24 \\\n"
            "    --write-version-file\n"
        ),
    )
    parser.add_argument(
        "--version",
        help="Optional base stable version (overrides VERSION file), e.g. 0.5.24",
    )
    parser.add_argument(
        "--backend-version",
        help="Optional backend-specific stable version (defaults to --version/VERSION)",
    )
    parser.add_argument(
        "--tauri-version",
        help="Optional Tauri-specific stable version (defaults to backend version)",
    )
    parser.add_argument(
        "--frontend-version",
        help="Optional frontend-specific stable version (defaults to Tauri version)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print derived versions only")
    parser.add_argument(
        "--write-version-file",
        action="store_true",
        help="When --version is provided, also write it to VERSION",
    )
    args = parser.parse_args()

    version = read_version(args.version)
    validate_stable_version(version, field="base version")

    if args.version and args.write_version_file:
        VERSION_FILE.write_text(version + "\n", encoding="utf-8")

    for line in run_updates(
        base_version=version,
        dry_run=args.dry_run,
        backend_version=args.backend_version,
        tauri_version=args.tauri_version,
        frontend_version=args.frontend_version,
    ):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
