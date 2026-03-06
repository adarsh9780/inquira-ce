"""Helpers for wrapping analysis code with standardized artifact capture."""

from __future__ import annotations

import ast
import json
import re
from typing import Any


_KIND_ALIASES = {
    "dataframe": "dataframe",
    "pandas": "dataframe",
    "polars": "dataframe",
    "pyarrow": "dataframe",
    "arrow": "dataframe",
    "figure": "figure",
    "chart": "figure",
    "plotly": "figure",
    "scalar": "scalar",
    "value": "scalar",
    "number": "scalar",
    "text": "scalar",
}


def _normalize_capture_candidate_names(candidates: Any, *, max_items: int = 24) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    if not isinstance(candidates, list):
        return normalized

    limit = max(1, int(max_items))
    for item in candidates:
        if len(normalized) >= limit:
            break
        name = str(item or "").strip()
        if not name:
            continue
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            continue
        if name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def infer_capture_candidate_names(code: Any, *, max_items: int = 24) -> list[str]:
    """Infer likely output variable names from user-authored assignment statements."""
    body = str(code or "").strip()
    if not body:
        return []

    try:
        tree = ast.parse(body)
    except SyntaxError:
        return []

    names: list[str] = []
    seen: set[str] = set()
    limit = max(1, int(max_items))

    def _add_name(raw: Any) -> None:
        if len(names) >= limit:
            return
        name = str(raw or "").strip()
        if not name:
            return
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            return
        if name in seen:
            return
        seen.add(name)
        names.append(name)

    def _collect_target(target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            _add_name(target.id)
            return
        if isinstance(target, ast.Starred):
            _collect_target(target.value)
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                _collect_target(item)

    class _CandidateVisitor(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
            for target in node.targets:
                _collect_target(target)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
            _collect_target(node.target)
            self.generic_visit(node)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
            _collect_target(node.target)
            self.generic_visit(node)

        def visit_NamedExpr(self, node: ast.NamedExpr) -> None:  # noqa: N802
            _collect_target(node.target)
            self.generic_visit(node)

        def visit_Expr(self, node: ast.Expr) -> None:  # noqa: N802
            if isinstance(node.value, ast.Name):
                _add_name(node.value.id)
            self.generic_visit(node)

    _CandidateVisitor().visit(tree)
    return names


def normalize_output_contract(contract: Any, *, max_items: int = 8) -> list[dict[str, str]]:
    """Normalize output contract entries from model output."""
    if not isinstance(contract, list):
        return []

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in contract:
        if not isinstance(item, dict):
            continue
        raw_name = str(item.get("name") or "").strip()
        if not raw_name or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", raw_name) is None:
            continue
        key = raw_name.lower()
        if key in seen:
            continue
        raw_kind = str(item.get("kind") or "").strip().lower()
        kind = _KIND_ALIASES.get(raw_kind, "")
        if kind not in {"dataframe", "figure", "scalar"}:
            continue
        seen.add(key)
        normalized.append({"name": raw_name, "kind": kind})
        if len(normalized) >= max(1, int(max_items)):
            break
    return normalized


def build_auto_capture_result_code(
    output_contract: list[dict[str, str]],
    *,
    fallback_candidates: list[str] | None = None,
) -> str:
    """Build helper script that exports declared (or inferred) final outputs."""
    declared_contract = json.dumps(
        normalize_output_contract(output_contract),
        ensure_ascii=True,
    )
    fallback_names = json.dumps(
        _normalize_capture_candidate_names(fallback_candidates or []),
        ensure_ascii=True,
    )
    return (
        "import json as _json\n"
        "import sys as _inq_sys\n"
        "try:\n"
        "    import pandas as _inq_pd\n"
        "except Exception:\n"
        "    _inq_pd = None\n"
        "try:\n"
        "    import polars as _inq_pl\n"
        "except Exception:\n"
        "    _inq_pl = None\n"
        "try:\n"
        "    import pyarrow as _inq_pa\n"
        "except Exception:\n"
        "    _inq_pa = None\n"
        "try:\n"
        "    import plotly.graph_objects as _inq_go\n"
        "except Exception:\n"
        "    _inq_go = None\n"
        f"_inq_declared = _json.loads(r'''{declared_contract}''')\n"
        f"_inq_fallback_names = _json.loads(r'''{fallback_names}''')\n"
        "if not isinstance(_inq_declared, list):\n"
        "    _inq_declared = []\n"
        "if not isinstance(_inq_fallback_names, list):\n"
        "    _inq_fallback_names = []\n"
        "_inq_capture_errors = []\n"
        "def _inq_record_error(name, kind, exc):\n"
        "    _inq_capture_errors.append({\n"
        "        'name': str(name or ''),\n"
        "        'kind': str(kind or ''),\n"
        "        'error': str(exc),\n"
        "    })\n"
        "def _inq_kind_of(obj):\n"
        "    if _inq_go is not None and isinstance(obj, _inq_go.Figure):\n"
        "        return 'figure'\n"
        "    if _inq_pd is not None and isinstance(obj, _inq_pd.DataFrame):\n"
        "        return 'dataframe'\n"
        "    if _inq_pl is not None and isinstance(obj, (_inq_pl.DataFrame, _inq_pl.LazyFrame)):\n"
        "        return 'dataframe'\n"
        "    if _inq_pa is not None and isinstance(obj, (_inq_pa.Table, _inq_pa.RecordBatch)):\n"
        "        return 'dataframe'\n"
        "    if _inq_pa is not None and hasattr(_inq_pa, 'RecordBatchReader') and isinstance(obj, _inq_pa.RecordBatchReader):\n"
        "        return 'dataframe'\n"
        "    return 'scalar'\n"
        "def _inq_to_pandas(obj):\n"
        "    if _inq_pd is not None and isinstance(obj, _inq_pd.DataFrame):\n"
        "        return obj\n"
        "    if _inq_pl is not None and isinstance(obj, _inq_pl.LazyFrame):\n"
        "        return obj.collect().to_pandas()\n"
        "    if _inq_pl is not None and isinstance(obj, _inq_pl.DataFrame):\n"
        "        return obj.to_pandas()\n"
        "    if _inq_pa is not None and isinstance(obj, _inq_pa.Table):\n"
        "        return obj.to_pandas()\n"
        "    if _inq_pa is not None and isinstance(obj, _inq_pa.RecordBatch):\n"
        "        return _inq_pa.Table.from_batches([obj]).to_pandas()\n"
        "    if _inq_pa is not None and hasattr(_inq_pa, 'RecordBatchReader') and isinstance(obj, _inq_pa.RecordBatchReader):\n"
        "        return obj.read_all().to_pandas()\n"
        "    return None\n"
        "for _inq_item in list(_inq_declared):\n"
        "    if not isinstance(_inq_item, dict):\n"
        "        continue\n"
        "    _inq_name = str(_inq_item.get('name') or '').strip()\n"
        "    _inq_kind = str(_inq_item.get('kind') or '').strip().lower()\n"
        "    if not _inq_name or _inq_name not in globals():\n"
        "        continue\n"
        "    _inq_obj = globals().get(_inq_name)\n"
        "    try:\n"
        "        if _inq_kind == 'dataframe':\n"
        "            _inq_pdf = _inq_to_pandas(_inq_obj)\n"
        "            if _inq_pdf is not None:\n"
        "                export_dataframe(_inq_pdf, logical_name=_inq_name)\n"
        "        elif _inq_kind == 'figure':\n"
        "            if _inq_go is not None and isinstance(_inq_obj, _inq_go.Figure):\n"
        "                export_figure(_inq_obj, logical_name=_inq_name)\n"
        "        elif _inq_kind == 'scalar':\n"
        "            export_scalar(_inq_obj, logical_name=_inq_name)\n"
        "    except Exception as _inq_exc:\n"
        "        _inq_record_error(_inq_name, _inq_kind, _inq_exc)\n"
        "if not _inq_declared:\n"
        "    _inq_aliases = ('result', 'final_df', 'df', 'fig', 'figure')\n"
        "    _inq_candidate_names = list(_inq_aliases)\n"
        "    for _inq_name in _inq_fallback_names:\n"
        "        if isinstance(_inq_name, str) and _inq_name and _inq_name not in _inq_candidate_names:\n"
        "            _inq_candidate_names.append(_inq_name)\n"
        "    _inq_exported_any = False\n"
        "    for _inq_name in _inq_candidate_names:\n"
        "        if _inq_name not in globals():\n"
        "            continue\n"
        "        _inq_obj = globals().get(_inq_name)\n"
        "        try:\n"
        "            _inq_kind = _inq_kind_of(_inq_obj)\n"
        "            if _inq_kind == 'dataframe':\n"
        "                _inq_pdf = _inq_to_pandas(_inq_obj)\n"
        "                if _inq_pdf is not None:\n"
        "                    export_dataframe(_inq_pdf, logical_name=_inq_name)\n"
        "                    _inq_exported_any = True\n"
        "            elif _inq_kind == 'figure':\n"
        "                export_figure(_inq_obj, logical_name=_inq_name)\n"
        "                _inq_exported_any = True\n"
        "            elif _inq_kind == 'scalar' and _inq_name in _inq_aliases:\n"
        "                export_scalar(_inq_obj, logical_name=_inq_name)\n"
        "                _inq_exported_any = True\n"
        "        except Exception as _inq_exc:\n"
        "            _inq_record_error(_inq_name, 'auto-candidate', _inq_exc)\n"
        "    if (not _inq_exported_any) and ('_' in globals()):\n"
        "        _inq_name = 'result'\n"
        "        _inq_obj = globals().get('_')\n"
        "        try:\n"
        "            _inq_kind = _inq_kind_of(_inq_obj)\n"
        "            if _inq_kind == 'dataframe':\n"
        "                _inq_pdf = _inq_to_pandas(_inq_obj)\n"
        "                if _inq_pdf is not None:\n"
        "                    export_dataframe(_inq_pdf, logical_name=_inq_name)\n"
        "            elif _inq_kind == 'figure':\n"
        "                export_figure(_inq_obj, logical_name=_inq_name)\n"
        "            else:\n"
        "                export_scalar(_inq_obj, logical_name=_inq_name)\n"
        "        except Exception as _inq_exc:\n"
        "            _inq_record_error(_inq_name, 'auto-fallback', _inq_exc)\n"
        "if _inq_capture_errors:\n"
        "    for _inq_err in _inq_capture_errors:\n"
        "        _inq_name = _inq_err.get('name') or 'unknown'\n"
        "        _inq_kind = _inq_err.get('kind') or 'unknown'\n"
        "        _inq_message = _inq_err.get('error') or 'unknown error'\n"
        "        print('[auto-capture] failed to export ' + str(_inq_kind) + ':' + str(_inq_name) + ' -> ' + str(_inq_message), file=_inq_sys.stderr)\n"
    )


def build_run_wrapped_code(code: str, run_id: str, output_contract: list[dict[str, str]]) -> str:
    """Wrap analysis code with active run setup and output capture footer."""
    body = str(code or "").rstrip()
    if not body:
        return ""
    auto_capture_code = build_auto_capture_result_code(
        output_contract,
        fallback_candidates=infer_capture_candidate_names(body),
    )
    return f"set_active_run({run_id!r})\n{body}\n{auto_capture_code}\n"
