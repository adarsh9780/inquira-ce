from fastapi import APIRouter, Request, HTTPException
from starlette.concurrency import run_in_threadpool
import os
import sys
import subprocess
import shutil

router = APIRouter(prefix="/system", tags=["System"])


def _pick_file_tk() -> str:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    try:
        path = filedialog.askopenfilename()
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return path


def _pick_file_osascript() -> str:
    """macOS: Use AppleScript file chooser via osascript"""
    try:
        script = 'POSIX path of (choose file with prompt "Select data file for Inquira")'
        out = subprocess.check_output(["osascript", "-e", script], text=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        # User cancelled or error; treat as no selection
        return ""
    except FileNotFoundError:
        # osascript not available
        return ""


def _pick_file_zenity() -> str:
    """Linux: Use zenity file selection if available (requires GUI session)."""
    if not shutil.which("zenity"):
        return ""
    try:
        out = subprocess.check_output(["zenity", "--file-selection", "--title=Select data file for Inquira"], text=True)
        return out.strip()
    except subprocess.CalledProcessError:
        # Cancelled or error
        return ""


def _pick_file_cross_platform() -> str:
    """Try platform-appropriate pickers, with sensible fallbacks.

    Order:
    - macOS: osascript first (non-blocking for Tk), then Tkinter
    - Linux: zenity if present, then Tkinter
    - Windows: Tkinter
    """
    plat = sys.platform
    # macOS
    if plat == "darwin":
        path = _pick_file_osascript()
        if path:
            return path
        try:
            return _pick_file_tk()
        except Exception:
            return ""
    # Linux
    if plat.startswith("linux"):
        path = _pick_file_zenity()
        if path:
            return path
        try:
            return _pick_file_tk()
        except Exception:
            return ""
    # Windows or others: try Tk
    try:
        return _pick_file_tk()
    except Exception:
        return ""


@router.post("/open-file-dialog")
async def open_file_dialog(request: Request):
    """Open a native OS file dialog on the local machine and return the absolute path.

    Safety/Scope:
    - Only enabled when env var `INQUIRA_ALLOW_FILE_DIALOG=1` is set.
    - Only accepts requests from localhost (127.0.0.1/::1).
    - No file content is uploaded; only the absolute path string is returned.
    """
    if os.getenv("INQUIRA_ALLOW_FILE_DIALOG") != "1":
        raise HTTPException(status_code=403, detail="File dialog disabled")

    client = request.client.host if request and request.client else None
    if client not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Local requests only")

    try:
        # Run dialog in a thread to avoid blocking the event loop
        path = await run_in_threadpool(_pick_file_cross_platform)
        if not path:
            raise HTTPException(status_code=400, detail="No file selected")
        return {"data_path": os.path.abspath(path)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dialog failed: {e}")
