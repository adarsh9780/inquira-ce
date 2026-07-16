"""Minimal worker entry point reserved for the next milestone."""

from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({"service": "inquira-data-worker", "status": "ready"}))


if __name__ == "__main__":
    main()
