"""Export FastAPI OpenAPI schema to a JSON file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.main import app


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote OpenAPI schema to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
