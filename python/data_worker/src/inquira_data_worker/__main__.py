"""Concurrent JSON-lines entry point for the persistent local worker."""

from __future__ import annotations

import asyncio
import json
import sys

from .runtime import WorkerRuntime


async def _serve() -> None:
    runtime = WorkerRuntime()
    output_lock = asyncio.Lock()
    tasks: set[asyncio.Task[None]] = set()

    async def write(payload: dict) -> None:
        async with output_lock:
            print(json.dumps(payload, ensure_ascii=False), flush=True)

    async def handle_line(line: str) -> None:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            await write({"id": None, "result": None, "error": {"code": "invalid_json", "message": "Request was not valid JSON."}})
            return

        request_id = request.get("id") if isinstance(request, dict) else None

        async def emit(event: dict) -> None:
            await write({"id": request_id, "event": {"type": event.get("type", "event"), "data": event}})

        response = await runtime.handle(request, emit)
        await write(response)

    try:
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if line == "":
                break
            task = asyncio.create_task(handle_line(line))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await runtime.shutdown()


def main() -> None:
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
