#!/usr/bin/env python3
"""Print current version values from all version-bearing source files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "VERSION"
BACKEND_PYPROJECT = ROOT / "backend" / "pyproject.toml"
BACKEND_LOCK = ROOT / "backend" / "uv.lock"
BACKEND_MAIN = ROOT / "backend" / "app" / "main.py"
TAURI_CARGO = ROOT / "src-tauri" / "Cargo.toml"
TAURI_CONF = ROOT / "src-tauri" / "tauri.conf.json"
FRONTEND_PACKAGE = ROOT / "frontend" / "package.json"
FRONTEND_LOCK = ROOT / "frontend" / "package-lock.json"


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


def _read_backend_lock_project_version(path: Path) -> str | None:
    return _read_regex(
        path,
        r'\[\[package\]\]\nname = "inquira-ce"\nversion = "([^"]+)"',
    )


def collect_versions() -> dict[str, str]:
    values: dict[str, str] = {}
    values["VERSION"] = VERSION_FILE.read_text(encoding="utf-8").strip()
    values["backend/pyproject.toml.version"] = _read_regex(
        BACKEND_PYPROJECT, r'^version\s*=\s*"([^"]+)"'
    ) or "<missing>"
    values["backend/uv.lock.inquira-ce.version"] = (
        _read_backend_lock_project_version(BACKEND_LOCK) or "<missing>"
    )
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
    return values


def versions_aligned(values: dict[str, str]) -> bool:
    return len(set(values.values())) == 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print current version values.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Exit non-zero when source-owned version files are not aligned.",
    )
    args = parser.parse_args(argv)

    values = collect_versions()
    for key, value in values.items():
        print(f"{key}={value}")
    if args.verify and not versions_aligned(values):
        print("version mismatch detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
