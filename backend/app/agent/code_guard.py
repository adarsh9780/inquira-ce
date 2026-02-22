from dataclasses import dataclass


@dataclass
class CodeGuardResult:
    code: str
    changed: bool
    blocked: bool
    should_retry: bool = False
    reason: str | None = None


def guard_code(
    code: str, table_name: str | None = None, allow_fallback: bool = True
) -> CodeGuardResult:
    raw = (code or "").strip()
    if not raw:
        return CodeGuardResult(
            code="",
            changed=False,
            blocked=True,
            should_retry=True,
            reason="Empty code.",
        )

    if "await query(" in raw:
        return CodeGuardResult(
            code=raw,
            changed=False,
            blocked=True,
            should_retry=True,
            reason=(
                "Legacy `await query(...)` bridge detected. "
                "Use `conn.sql(...).fetchdf()` with a backend DuckDB connection."
            ),
        )

    return CodeGuardResult(code=raw, changed=False, blocked=False, reason=None)
