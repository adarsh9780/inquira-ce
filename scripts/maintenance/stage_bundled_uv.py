#!/usr/bin/env python3
"""Stage local uv binary into src-tauri/bundled-tools for desktop builds."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET_DIR = ROOT / "src-tauri" / "bundled-tools"


def main() -> int:
    uv_path = shutil.which("uv")
    if not uv_path:
        print("Could not find uv in PATH.")
        return 1

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    source = Path(uv_path)

    if platform.system().lower().startswith("win"):
        target = TARGET_DIR / "uv.exe"
    else:
        target = TARGET_DIR / "uv"

    shutil.copy2(source, target)
    if target.name == "uv":
        target.chmod(0o755)
    print(f"staged={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
