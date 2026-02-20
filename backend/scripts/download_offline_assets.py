#!/usr/bin/env python3
import os
import sys
import urllib.request
import tarfile
import subprocess
from pathlib import Path


def download_pyodide(target_dir: Path):
    print("Downloading Pyodide 0.27.2...")
    url = "https://github.com/pyodide/pyodide/releases/download/0.27.2/pyodide-0.27.2.tar.bz2"
    tar_path = target_dir / "pyodide-0.27.2.tar.bz2"

    urllib.request.urlretrieve(url, tar_path)
    print("Extracting Pyodide...")
    with tarfile.open(tar_path, "r:bz2") as tar:
        tar.extractall(path=target_dir)
    os.remove(tar_path)

    # The tarball extracts into a 'pyodide' subfolder, we want the contents in the target_dir
    extracted_dir = target_dir / "pyodide"
    if extracted_dir.exists():
        for item in extracted_dir.iterdir():
            item.rename(target_dir / item.name)
        extracted_dir.rmdir()
    print("Pyodide downloaded and extracted.")


def download_wheels(target_dir: Path):
    print("Downloading fallback wheels...")

    # We use uv to download pure-python wheels for ibis and its dependencies.
    # We don't download pandas from PyPI because Pyodide already includes a pandas wasm wheel in its tarball.
    packages = ["ibis-framework[duckdb]"]

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--platform",
        "any",  # Ibis is pure python
        "--python-version",
        "3.13",
        "--dest",
        str(target_dir),
    ] + packages

    try:
        subprocess.run(cmd, check=True)
        print("Fallback wheels downloaded successfully.")
    except Exception as e:
        print(f"Failed to download wheels: {e}")


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent / "app" / "static"
    pyodide_dir = base_dir / "pyodide"
    wheels_dir = base_dir / "wheels"

    pyodide_dir.mkdir(parents=True, exist_ok=True)
    wheels_dir.mkdir(parents=True, exist_ok=True)

    # We skip pyodide if it already exists to save time during local dev
    if not (pyodide_dir / "pyodide.js").exists():
        download_pyodide(pyodide_dir)
    else:
        print("Pyodide already exists, skipping download.")

    download_wheels(wheels_dir)
    print("\nOffline assets successfully built!")
