#!/usr/bin/env python3
"""Check local uv version against the pinned project version."""

from __future__ import annotations

import argparse
import re
import subprocess


VERSION_RE = re.compile(r"\b(\d+\.\d+\.\d+)\b")


def parse_uv_version(output: str) -> str | None:
    match = VERSION_RE.search(output)
    if not match:
        return None
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate uv version.")
    parser.add_argument("--expected", required=True, help="Pinned uv version, e.g. 0.6.3")
    args = parser.parse_args()

    completed = subprocess.run(
        ["uv", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        print(f"failed to run uv --version: {stderr or 'unknown error'}")
        return 1

    actual = parse_uv_version(completed.stdout or "")
    if not actual:
        print(f"could not parse uv version from output: {(completed.stdout or '').strip()!r}")
        return 1

    if actual != args.expected:
        print(f"uv version mismatch: expected {args.expected}, found {actual}.")
        print(
            f"Please install or switch to uv {args.expected} to keep local builds aligned with GitHub releases."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
