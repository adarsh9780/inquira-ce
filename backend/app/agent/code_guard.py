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

    forbidden_loader_patterns = [
        r"\bread_csv_auto\s*\(",
        r"\bread_parquet\s*\(",
        r"\bread_json_auto\s*\(",
        r"\bread_json\s*\(",
        r"\bread_excel\s*\(",
        r"\bread_csv\s*\(",
        r"\bpd\.read_csv\s*\(",
        r"\bpd\.read_parquet\s*\(",
        r"\bpd\.read_json\s*\(",
        r"\bpd\.read_excel\s*\(",
    ]
    if any(re.search(pattern, raw) for pattern in forbidden_loader_patterns):
        return CodeGuardResult(
            code=raw,
            changed=False,
            blocked=True,
            should_retry=True,
            reason=(
                "Source-file loaders are not allowed in generated analysis code. "
                "Reuse the backend workspace DuckDB connection (`conn`) and query the registered table directly."
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
