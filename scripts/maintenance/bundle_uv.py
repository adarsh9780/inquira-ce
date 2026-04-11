"""Copy the active uv executable into the Tauri bundled tools directory."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUNDLED_TOOLS_DIR = ROOT / "src-tauri" / "bundled-tools"


def find_uv_binary() -> Path:
    uv_path = shutil.which("uv")
    if not uv_path:
        raise RuntimeError("uv binary not found on PATH.")
    return Path(uv_path)


def bundle_uv_binary(*, root: Path = ROOT, uv_path: Path | None = None) -> Path:
    source = uv_path or find_uv_binary()
    if not source.is_file():
        raise RuntimeError(f"uv binary not found at {source}")

    destination_dir = root / "src-tauri" / "bundled-tools"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    shutil.copy2(source, destination)

    if os.name != "nt":
        current_mode = destination.stat().st_mode
        destination.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return destination


def main() -> int:
    destination = bundle_uv_binary()
    print(f"Bundled uv at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
