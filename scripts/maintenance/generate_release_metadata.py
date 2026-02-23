#!/usr/bin/env python3
"""Generate .github/release/metadata.json from release_metadata.md.

Input markdown format (simple):
- First non-empty line is used as release title. Leading '#' is allowed.
- Remaining content is used as release body.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "VERSION"
SOURCE_MD = ROOT / "release_metadata.md"
TARGET_JSON = ROOT / ".github" / "release" / "metadata.json"


def _read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


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


def build_metadata_payload(version: str, title: str, body: str) -> dict[str, str]:
    tag = version if version.startswith("v") else f"v{version}"
    return {
        "version": version.removeprefix("v"),
        "tag": tag,
        "release_name": title,
        "release_body": body,
    }


def write_metadata_file(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate release metadata JSON from release_metadata.md."
    )
    parser.add_argument(
        "--source",
        default=str(SOURCE_MD),
        help="Path to source markdown file (default: release_metadata.md).",
    )
    parser.add_argument(
        "--output",
        default=str(TARGET_JSON),
        help="Path to output JSON file (default: .github/release/metadata.json).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Optional release version override; defaults to VERSION file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated payload without writing output file.",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(
            f"Source metadata markdown not found: {source}. "
            "Create release_metadata.md in repo root first."
        )

    version = (args.version or _read_version()).strip()
    if not version:
        raise ValueError("Release version is empty")

    title, body = parse_release_metadata_markdown(source.read_text(encoding="utf-8"))
    payload = build_metadata_payload(version=version, title=title, body=body)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    write_metadata_file(output, payload)
    print(f"Wrote release metadata: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
