"""JSON-lines entry point for the local data worker."""

from __future__ import annotations

import json
import sys

from .rpc import handle_request


def main() -> None:
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {"id": None, "result": None, "error": {"code": "invalid_json", "message": "Request was not valid JSON."}}
        else:
            response = handle_request(request)
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
