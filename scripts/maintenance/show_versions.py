#!/usr/bin/env python3
"""Print current version values from all version-bearing project files."""

from __future__ import annotations

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
INSTALL_SH = ROOT / "scripts" / "install-inquira.sh"
INSTALL_PS1 = ROOT / "scripts" / "install-inquira.ps1"
RELEASE_METADATA = ROOT / ".github" / "release" / "metadata.json"


def _read_regex(path: Path, pattern: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text, flags=re.MULTILINE)
    if match:
        return match.group(1)
    return None


def _read_json_key(path: Path, key: str) -> str | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get(key)
    if isinstance(value, str):
        return value
    return None


def _read_frontend_lock_root_version(path: Path) -> str | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    packages = payload.get("packages")
    if not isinstance(packages, dict):
        return None
    root_pkg = packages.get("")
    if not isinstance(root_pkg, dict):
        return None
    value = root_pkg.get("version")
    if isinstance(value, str):
        return value
    return None


def _read_wheel_url_version(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    pattern = (
        r"https://github\.com/adarsh9780/inquira-ce/releases/download/"
        r"v([^/]+)/inquira_ce-[^-]+-py3-none-any\.whl"
    )
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def collect_versions() -> dict[str, str]:
    values: dict[str, str] = {}
    values["VERSION"] = VERSION_FILE.read_text(encoding="utf-8").strip()
    values["backend/pyproject.toml.version"] = _read_regex(
        BACKEND_PYPROJECT, r'^version\s*=\s*"([^"]+)"'
    ) or "<missing>"
    values["backend/app/main.py.APP_VERSION"] = _read_regex(
        BACKEND_MAIN, r'^APP_VERSION\s*=\s*"([^"]+)"'
    ) or "<missing>"
    values["src-tauri/Cargo.toml.version"] = _read_regex(
        TAURI_CARGO, r'^version\s*=\s*"([^"]+)"'
    ) or "<missing>"
    values["src-tauri/tauri.conf.json.version"] = (
        _read_json_key(TAURI_CONF, "version") or "<missing>"
    )
    values["frontend/package.json.version"] = (
        _read_json_key(FRONTEND_PACKAGE, "version") or "<missing>"
    )
    values["frontend/package-lock.json.version"] = (
        _read_json_key(FRONTEND_LOCK, "version") or "<missing>"
    )
    values["frontend/package-lock.json.packages[''].version"] = (
        _read_frontend_lock_root_version(FRONTEND_LOCK) or "<missing>"
    )
    values["scripts/install-inquira.sh.wheel_version"] = (
        _read_wheel_url_version(INSTALL_SH) or "<missing>"
    )
    values["scripts/install-inquira.ps1.wheel_version"] = (
        _read_wheel_url_version(INSTALL_PS1) or "<missing>"
    )
    if RELEASE_METADATA.exists():
        values[".github/release/metadata.json.version"] = (
            _read_json_key(RELEASE_METADATA, "version") or "<missing>"
        )
        values[".github/release/metadata.json.tag"] = (
            _read_json_key(RELEASE_METADATA, "tag") or "<missing>"
        )
    return values


def main() -> int:
    for key, value in collect_versions().items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
