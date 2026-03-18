from __future__ import annotations

from .config import AgentServiceConfig


_tracing_initialized = False


def init_phoenix_tracing(cfg: AgentServiceConfig) -> bool:
    global _tracing_initialized
    if _tracing_initialized:
        return True
    if not cfg.phoenix.enabled:
        return False
    try:
        from phoenix.otel import register

        kwargs = {"project_name": cfg.phoenix.project, "auto_instrument": True}
        if cfg.phoenix.endpoint:
            kwargs["endpoint"] = cfg.phoenix.endpoint
        register(**kwargs)
        _tracing_initialized = True
        return True
    except Exception:
        return False
