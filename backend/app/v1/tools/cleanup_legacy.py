"""CLI command to inspect and clean legacy local artifacts."""

from __future__ import annotations

import argparse
import json

from ..services.legacy_cleanup_service import LegacyCleanupService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inquira-cleanup-legacy",
        description="Inspect and optionally prune legacy local artifacts under ~/.inquira",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply cleanup changes. Without this flag, command runs in dry-run mode.",
    )
    args = parser.parse_args(argv)

    report = LegacyCleanupService.run_cleanup(dry_run=not args.apply)
    payload = {
        "dry_run": report.dry_run,
        "removed_paths": report.removed_paths,
        "blocked_paths": report.blocked_paths,
        "details": report.details,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
