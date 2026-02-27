from dataclasses import dataclass
import re


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

    # Plotly Express does not accept Narwhals wrapper DataFrames directly.
    # Catch the common failure pattern and request regeneration.
    narwhals_vars = set(
        re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*nw\.from_native\(", raw, flags=re.MULTILINE)
    )
    for var_name in narwhals_vars:
        direct_positional = re.search(
            rf"px\.\w+\(\s*{re.escape(var_name)}\s*(?:,|\))", raw
        )
        direct_keyword = re.search(
            rf"px\.\w+\([^)]*data_frame\s*=\s*{re.escape(var_name)}\b",
            raw,
            flags=re.DOTALL,
        )
        if direct_positional or direct_keyword:
            return CodeGuardResult(
                code=raw,
                changed=False,
                blocked=True,
                should_retry=True,
                reason=(
                    "Plotly requires a native/pandas dataframe, not a Narwhals wrapper. "
                    "Convert with `nw.to_native(...)` then `.to_pandas()` (or `pd.DataFrame(...)`) "
                    "before calling `px.*`."
                ),
            )

    return CodeGuardResult(code=raw, changed=False, blocked=False, reason=None)
