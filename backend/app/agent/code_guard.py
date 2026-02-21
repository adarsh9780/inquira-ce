import re
from dataclasses import dataclass


_FORBIDDEN_PATTERNS = [
    re.compile(r"\bibis\.duckdb\.connect\s*\("),
    re.compile(r"\bduckdb\.connect\s*\("),
    re.compile(r"\b(?:con|conn)\.read_csv\s*\("),
    re.compile(r"\b(?:con|conn)\.read_parquet\s*\("),
]


@dataclass
class CodeGuardResult:
    code: str
    changed: bool
    blocked: bool
    should_retry: bool = False
    reason: str | None = None


def _rewrite_common_patterns(code: str) -> str:
    updated = code

    # Convert common DuckDB Python execution patterns to bridge usage.
    updated = re.sub(
        r"(?m)^(\s*\w+\s*=\s*)(?:con|conn)\.sql\((.+?)\)\.(?:fetchdf|df|execute)\(\)\s*$",
        r"\1await query(\2)",
        updated,
    )
    updated = re.sub(
        r"(?m)^(?:\s*)(?:con|conn)\.sql\((.+?)\)\.(?:fetchdf|df|execute)\(\)\s*$",
        r"await query(\1)",
        updated,
    )

    # Remove known-invalid setup lines for browser bridge execution.
    kept_lines: list[str] = []
    for line in updated.splitlines():
        stripped = line.strip()
        if stripped.startswith("import duckdb"):
            continue
        if "duckdb.connect(" in line:
            continue
        if "ibis.duckdb.connect(" in line:
            continue
        if ".read_csv(" in line and ("con." in line or "conn." in line):
            continue
        if ".read_parquet(" in line and ("con." in line or "conn." in line):
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines)


def _contains_forbidden_patterns(code: str) -> bool:
    return any(pattern.search(code) for pattern in _FORBIDDEN_PATTERNS)


def _has_bridge_query(code: str) -> bool:
    return re.search(r"\bawait\s+query\s*\(", code) is not None


def build_bridge_fallback_code(table_name: str | None = None) -> str:
    safe_table_name = table_name or "data_table"
    return (
        "import pandas as pd\n\n"
        f'table_name = "{safe_table_name}"\n'
        "_guard_df = await query(f\"SELECT * FROM {table_name} LIMIT 100\")\n"
        "_guard_df\n"
    )


def guard_code(
    code: str, table_name: str | None = None, allow_fallback: bool = True
) -> CodeGuardResult:
    raw = (code or "").strip()
    if not raw:
        if allow_fallback:
            return CodeGuardResult(
                code=build_bridge_fallback_code(table_name),
                changed=True,
                blocked=False,
            )
        return CodeGuardResult(
            code="",
            changed=False,
            blocked=True,
            should_retry=True,
            reason="Empty code.",
        )

    rewritten = _rewrite_common_patterns(raw)
    changed = rewritten != raw

    if _contains_forbidden_patterns(rewritten):
        if allow_fallback:
            return CodeGuardResult(
                code=build_bridge_fallback_code(table_name),
                changed=True,
                blocked=False,
            )
        return CodeGuardResult(
            code="",
            changed=changed,
            blocked=True,
            should_retry=True,
            reason="Generated code still uses unsupported DuckDB Python APIs.",
        )

    if not _has_bridge_query(rewritten):
        if allow_fallback:
            rewritten = build_bridge_fallback_code(table_name)
            changed = True
        else:
            return CodeGuardResult(
                code="",
                changed=changed,
                blocked=True,
                should_retry=True,
                reason=(
                    "Generated code does not call the browser DuckDB bridge. "
                    "Use await query(...) with the active table."
                ),
            )

    return CodeGuardResult(code=rewritten, changed=changed, blocked=False, reason=None)
