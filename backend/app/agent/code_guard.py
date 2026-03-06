from dataclasses import dataclass
import ast
import re


@dataclass
class CodeGuardResult:
    code: str
    changed: bool
    blocked: bool
    should_retry: bool = False
    reason: str | None = None


def _contains_duckdb_connect(raw: str) -> bool:
    if re.search(r"\bduckdb\.connect\s*\(", raw):
        return True

    try:
        tree = ast.parse(raw)
    except SyntaxError:
        return False

    duckdb_aliases: set[str] = {"duckdb"}
    connect_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "duckdb":
                    duckdb_aliases.add(alias.asname or "duckdb")
        elif isinstance(node, ast.ImportFrom) and node.module == "duckdb":
            for alias in node.names:
                if alias.name in {"connect", "*"}:
                    connect_aliases.add(alias.asname or "connect")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if (
            isinstance(fn, ast.Attribute)
            and fn.attr == "connect"
            and isinstance(fn.value, ast.Name)
            and fn.value.id in duckdb_aliases
        ):
            return True
        if isinstance(fn, ast.Name) and fn.id in connect_aliases:
            return True

    return False


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

    if _contains_duckdb_connect(raw):
        return CodeGuardResult(
            code=raw,
            changed=False,
            blocked=True,
            should_retry=True,
            reason=(
                "Do not create a new DuckDB connection in generated code. "
                "Use the pre-provisioned read-only workspace connection `conn`."
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

    if re.search(r"\.to_dict\s*\(\s*(?:orient\s*=\s*)?['\"]records['\"]\s*\)", raw):
        return CodeGuardResult(
            code=raw,
            changed=False,
            blocked=True,
            should_retry=True,
            reason=(
                "Do not convert dataframe outputs to list/dict JSON (for example, `df.to_dict(orient='records')`). "
                "Keep dataframe variables as dataframe objects and reference them in `output_contract`."
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
