from __future__ import annotations

import uvicorn

from .config import load_agent_service_config


def run() -> None:
    cfg = load_agent_service_config()
    uvicorn.run(
        "runtime_server.service:create_app",
        host=cfg.host,
        port=int(cfg.port),
        factory=True,
        log_level="info",
    )


if __name__ == "__main__":
    run()
