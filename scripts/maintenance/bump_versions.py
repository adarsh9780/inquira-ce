#!/usr/bin/env python3
"""Bump project versions from a single source of truth.

Single source:
- VERSION (PEP 440, e.g. 0.5.0a1)

Targets:
- backend/pyproject.toml (PEP 440)
- backend/app/main.py APP_VERSION (PEP 440)
- src-tauri/Cargo.toml package.version (SemVer-compatible)
- src-tauri/tauri.conf.json version (SemVer-compatible)
- frontend/package.json version
- frontend/package-lock.json top-level version + packages[""].version
- scripts/install-inquira.sh default wheel URL (PEP 440 tag/wheel)
- scripts/install-inquira.ps1 default wheel URL (PEP 440 tag/wheel)
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
INSTALL_SH = ROOT / "scripts" / "install-inquira.sh"
INSTALL_PS1 = ROOT / "scripts" / "install-inquira.ps1"
FRONTEND_PACKAGE = ROOT / "frontend" / "package.json"
FRONTEND_LOCK = ROOT / "frontend" / "package-lock.json"


def normalize_version_input(version: str) -> str:
    """Accept optional leading tag marker and normalize to PEP 440 base input."""
    v = version.strip()
    if v.startswith("v"):
        return v[1:]
    return v


def pep440_to_tauri_semver(version: str) -> str:
    """Convert common PEP 440 prereleases to SemVer prerelease style.

    Examples:
    - 0.5.0a1 -> 0.5.0-alpha.1
    - 0.5.0b2 -> 0.5.0-beta.2
    - 0.5.0rc3 -> 0.5.0-rc.3
    - 0.5.0 -> 0.5.0
    """
    v = normalize_version_input(version)
    m = re.fullmatch(r"(\d+\.\d+\.\d+)(?:(a|b|rc)(\d+))?", v)
    if not m:
        raise ValueError(
            "Unsupported VERSION format. Use PEP 440 like 0.5.0, 0.5.0a1, 0.5.0b1, 0.5.0rc1"
        )
    base, label, num = m.groups()
    if not label:
        return base
    mapped = {"a": "alpha", "b": "beta", "rc": "rc"}[label]
    return f"{base}-{mapped}.{num}"


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
    effective_backend = (backend_version or base_version).strip()

    # Backend is Python, so validate as PEP 440-like.
    pep440_to_tauri_semver(effective_backend)

    effective_tauri = (tauri_version or pep440_to_tauri_semver(effective_backend)).strip()
    # Frontend/package.json should stay SemVer compatible by default.
    effective_frontend = (frontend_version or effective_tauri).strip()

    return {
        "base": base_version.strip(),
        "backend": effective_backend,
        "tauri": effective_tauri,
        "frontend": effective_frontend,
    }


def wheel_url_for(version: str) -> str:
    return (
        "https://github.com/adarsh9780/inquira-ce/releases/download/"
        f"v{version}/inquira_ce-{version}-py3-none-any.whl"
    )


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


def update_install_scripts(version: str) -> list[Path]:
    url = wheel_url_for(version)
    changed: list[Path] = []
    pattern = (
        r"https://github.com/adarsh9780/inquira-ce/releases/download/"
        r"[^/'\"\s]+/inquira_ce-[^/'\"\s]+-py3-none-any\.whl"
    )
    for path in (INSTALL_SH, INSTALL_PS1):
        if replace_text(path, pattern, url):
            changed.append(path)
    return changed


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
    wheel_url = wheel_url_for(versions["backend"])
    results: list[str] = [
        f"base_version={versions['base']}",
        f"backend_version={versions['backend']}",
        f"tauri_version={versions['tauri']}",
        f"frontend_version={versions['frontend']}",
        f"wheel_url={wheel_url}",
    ]
    if dry_run:
        return results

    changed: list[str] = []
    if update_backend_pyproject(versions["backend"]):
        changed.append("backend/pyproject.toml")
    if update_backend_main(versions["backend"]):
        changed.append("backend/app/main.py")
    if update_tauri_cargo(versions["tauri"]):
        changed.append("src-tauri/Cargo.toml")
    if update_tauri_conf(versions["tauri"]):
        changed.append("src-tauri/tauri.conf.json")
    if update_frontend_package(versions["frontend"]):
        changed.append("frontend/package.json")
    if update_frontend_lock(versions["frontend"]):
        changed.append("frontend/package-lock.json")
    changed.extend(
        str(p.relative_to(ROOT))
        for p in update_install_scripts(versions["backend"])
    )

    if changed:
        results.append("updated_files=" + ",".join(changed))
    else:
        results.append("updated_files=<none>")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump project versions from VERSION file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/maintenance/bump_versions.py --help\n"
            "  uv run python scripts/maintenance/bump_versions.py --version 0.5.0a1 --dry-run\n"
            "  uv run python scripts/maintenance/bump_versions.py --version 0.5.0a1 --write-version-file\n"
            "  uv run python scripts/maintenance/bump_versions.py \\\n"
            "    --version 0.5.0a1 \\\n"
            "    --backend-version 0.5.0a1 \\\n"
            "    --tauri-version 0.5.0-alpha.1 \\\n"
            "    --frontend-version 0.5.0-alpha.1 \\\n"
            "    --write-version-file\n"
        ),
    )
    parser.add_argument(
        "--version",
        help="Optional base PEP 440 version (overrides VERSION file), e.g. 0.5.0a1",
    )
    parser.add_argument(
        "--backend-version",
        help="Optional backend-specific PEP 440 version (defaults to --version/VERSION)",
    )
    parser.add_argument(
        "--tauri-version",
        help="Optional Tauri-specific version (defaults to SemVer mapping of backend version)",
    )
    parser.add_argument(
        "--frontend-version",
        help="Optional frontend-specific version (defaults to Tauri version for npm SemVer compatibility)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print derived versions only")
    parser.add_argument(
        "--write-version-file",
        action="store_true",
        help="When --version is provided, also write it to VERSION",
    )
    args = parser.parse_args()

    version = read_version(args.version)
    pep440_to_tauri_semver(version)  # Validate early

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
