from __future__ import annotations

import json

from app.services import workspace_kernel_manager as manager


def test_materialize_exports_template_uses_safe_sentinel_replacement() -> None:
    rendered = manager._MATERIALIZE_EXPORTS_TEMPLATE.replace(
        manager._MATERIALIZE_EXPORTS_SPECS_SENTINEL,
        json.dumps("[]"),
    )

    compile(rendered, "<materialize_exports>", "exec")
    assert "{_escaped_table}" in rendered
    assert "COPY (SELECT * FROM" in rendered
    assert "artifact_manifest" in rendered
    assert manager._MATERIALIZE_EXPORTS_SPECS_SENTINEL not in rendered
