#!/usr/bin/env python3
"""Cross-platform version validation helpers for Makefile targets."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


STABLE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def parse_stable(version: str) -> tuple[int, int, int]:
    value = version.strip()
    if not STABLE_VERSION_RE.fullmatch(value):
        raise ValueError(
            f"Unsupported version format: {version!r}. Use stable Major.Minor.Patch only, e.g. 0.5.24"
        )
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def read_version_file(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{path} is empty.")
    return value


def cmd_validate(args: argparse.Namespace) -> int:
    _ = parse_stable(args.version)
    print(f"version format check passed: {args.version}")
    return 0


def cmd_validate_file(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        raise ValueError(f"{args.path} is missing.")
    version = read_version_file(path)
    _ = parse_stable(version)
    print(f"version file check passed: {args.path}={version}")
    return 0


def cmd_greater(args: argparse.Namespace) -> int:
    current = read_version_file(Path(args.current_file))
    new = args.new_version.strip()
    current_triplet = parse_stable(current)
    new_triplet = parse_stable(new)
    if new_triplet <= current_triplet:
        raise ValueError(f"New version {new} must be greater than current VERSION {current}.")
    print(f"version check passed: {new} > {current}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate stable project versions.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate a single version string.")
    validate.add_argument("--version", required=True, help="Version value to validate.")
    validate.set_defaults(func=cmd_validate)

    validate_file = sub.add_parser("validate-file", help="Validate version from a file.")
    validate_file.add_argument("--path", required=True, help="Version file path.")
    validate_file.set_defaults(func=cmd_validate_file)

    greater = sub.add_parser(
        "greater", help="Ensure --new-version is greater than the version in --current-file."
    )
    greater.add_argument("--current-file", required=True, help="Path to VERSION file.")
    greater.add_argument("--new-version", required=True, help="Candidate version.")
    greater.set_defaults(func=cmd_greater)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ValueError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
