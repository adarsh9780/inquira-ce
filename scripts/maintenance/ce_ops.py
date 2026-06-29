#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
TAURI_DIR = ROOT / "src-tauri"
ENV_FILE = ROOT / ".env"


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def run(args: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> int:
    return subprocess.run(args, cwd=cwd, text=True, env=env).returncode


def output(args: list[str], *, cwd: Path = ROOT) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        key = key.strip()
        if key:
            values[key] = raw.strip().strip("'").strip('"')
    return values


def runtime_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(read_dotenv(ENV_FILE))
    return env


def repo_has_changes() -> bool:
    return bool(output(["git", "status", "--short"], cwd=ROOT))


def resolve_commit_args(args: argparse.Namespace) -> list[str] | None:
    message = (args.msg or "").strip()
    file_path = (args.file or "").strip()
    if message and file_path:
        fail("Provide either msg=... or file=..., not both.")
        return None
    if message:
        return ["-m", message]
    if not file_path:
        fail("Usage: make commit msg='describe the CE change'")
        print("   or: make commit file=/absolute/or/relative/path", file=sys.stderr)
        return None
    path = Path(file_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        fail(f"Commit message file not found: {file_path}")
        return None
    return ["-F", str(path)]


def current_branch() -> str | None:
    branch = output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT)
    if branch == "HEAD":
        return None
    return branch


def validate_tag(tag: str) -> bool:
    return re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+([-.][A-Za-z0-9]+)*", tag) is not None


def cmd_status(_: argparse.Namespace) -> int:
    return run(["git", "status"], cwd=ROOT)


def cmd_doctor(_: argparse.Namespace) -> int:
    required_tools = ["bash", "make", "uv", "npm", "cargo"]
    missing = [tool for tool in required_tools if shutil.which(tool) is None]
    if missing:
        print("Missing developer tools: " + ", ".join(missing), file=sys.stderr)
        return 1
    print("Developer tools found: bash, make, uv, npm, cargo")
    return 0


def cmd_dev(_: argparse.Namespace) -> int:
    env = runtime_env()
    if ENV_FILE.exists():
        print(f"Using CE env file: {ENV_FILE}")
    else:
        print(f"CE env file not found: {ENV_FILE}")

    npm_cmd = ["npm.cmd", "run", "dev"] if os.name == "nt" else ["npm", "run", "dev"]
    cargo_cmd = ["cargo", "tauri", "dev"]

    frontend_proc = subprocess.Popen(npm_cmd, cwd=FRONTEND_DIR, text=True, env=env)
    try:
        time.sleep(3)
        result = subprocess.run(cargo_cmd, cwd=TAURI_DIR, text=True, env=env)
        return result.returncode
    finally:
        if frontend_proc.poll() is None:
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                frontend_proc.kill()


def cmd_commit(args: argparse.Namespace) -> int:
    commit_args = resolve_commit_args(args)
    if commit_args is None:
        return 1
    if not repo_has_changes():
        return fail("No CE changes to commit.")
    if run(["git", "add", "-A", "--", "."], cwd=ROOT) != 0:
        return 1
    return run(["git", "commit", *commit_args], cwd=ROOT)


def cmd_push(_: argparse.Namespace) -> int:
    branch = current_branch()
    if branch is None:
        return fail("Cannot push from a detached HEAD.")
    result = run(["git", "push", "origin", branch], cwd=ROOT)
    if result == 0:
        print(f"Pushed CE branch {branch}")
    return result


def cmd_tag(args: argparse.Namespace) -> int:
    tag = args.tag.strip()
    if not validate_tag(tag):
        return fail("Tag must look like vX.Y.Z or vX.Y.Z-suffix.")
    if run(["git", "tag", "-a", tag, "-m", f"CE source milestone {tag}"], cwd=ROOT) != 0:
        return 1
    return run(["git", "push", "origin", tag], cwd=ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("dev").set_defaults(func=cmd_dev)

    commit = sub.add_parser("commit")
    commit.add_argument("--msg", default="")
    commit.add_argument("--file", default="")
    commit.set_defaults(func=cmd_commit)

    sub.add_parser("push").set_defaults(func=cmd_push)

    tag = sub.add_parser("tag")
    tag.add_argument("--tag", required=True)
    tag.set_defaults(func=cmd_tag)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, end="")
        if exc.stderr:
            print(exc.stderr, end="", file=sys.stderr)
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
