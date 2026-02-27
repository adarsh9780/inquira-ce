#!/usr/bin/env python3
"""Pretty terminal UX for frequently used Makefile targets."""

from __future__ import annotations

import argparse
import os
import subprocess
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]
    cwd: Path
    description: str


@dataclass(frozen=True)
class StepResult:
    step: Step
    returncode: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0


TARGET_STEPS: dict[str, list[Step]] = {
    "check-version-pretty": [
        Step(
            name="Check versions",
            command=["uv", "run", "python", "scripts/maintenance/show_versions.py"],
            cwd=ROOT,
            description="Verify version consistency across VERSION, backend, frontend, and packaging files.",
        )
    ],
    "ruff-test-pretty": [
        Step(
            name="Ruff checks",
            command=["uv", "run", "--group", "dev", "ruff", "check", "app/v1", "tests"],
            cwd=BACKEND_DIR,
            description="Run CI-aligned backend lint checks before tests to surface style and quality issues early.",
        )
    ],
    "mypy-test-pretty": [
        Step(
            name="Mypy checks",
            command=[
                "uv",
                "run",
                "--group",
                "dev",
                "mypy",
                "--config-file",
                "mypy.ini",
                "app/v1",
            ],
            cwd=BACKEND_DIR,
            description="Run CI-aligned backend type checks to catch interface and typing regressions.",
        )
    ],
    "test-backend-pretty": [
        Step(
            name="Backend tests",
            command=["uv", "run", "--group", "dev", "pytest"],
            cwd=BACKEND_DIR,
            description="Run backend pytest suite with normal verbose output and a clean summary panel.",
        )
    ],
    "test-frontend-pretty": [
        Step(
            name="Frontend install",
            command=["npm", "ci"],
            cwd=FRONTEND_DIR,
            description="Install frontend dependencies in a reproducible way before running frontend tests.",
        ),
        Step(
            name="Frontend tests",
            command=["npm", "test"],
            cwd=FRONTEND_DIR,
            description="Run frontend test suite after dependency sync succeeds.",
        ),
    ],
}
TARGET_STEPS["test-pretty"] = (
    TARGET_STEPS["ruff-test-pretty"]
    + TARGET_STEPS["mypy-test-pretty"]
    + TARGET_STEPS["test-backend-pretty"]
    + TARGET_STEPS["test-frontend-pretty"]
)


def _wrap_block(text: str, width: int, indent: int = 0) -> str:
    effective_width = max(40, width - indent)
    return textwrap.fill(
        text.strip(),
        width=effective_width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _format_output_block(raw: str, width: int, max_lines: int = 80) -> str:
    if not raw.strip():
        return "(no output)"
    lines = raw.rstrip().splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
        lines.insert(0, f"... output truncated to last {max_lines} lines ...")

    wrapped_lines: list[str] = []
    for line in lines:
        if not line.strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.append(
            textwrap.fill(
                line,
                width=max(40, width - 6),
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(wrapped_lines)


def _run_step(step: Step, console: Any, text_cls: Any, panel_cls: Any, verbose: bool) -> StepResult:
    command_display = " ".join(step.command)
    console.print()
    console.rule(text_cls(step.name, style="bold cyan"))
    console.print(
        _wrap_block(step.description, width=console.width - 6),
        style="dim",
    )
    console.print(f"[bold]cwd:[/bold] {step.cwd}")
    console.print(f"[bold]cmd:[/bold] {command_display}")

    start = time.perf_counter()
    with console.status(f"Running {step.name}...", spinner="dots"):
        proc = subprocess.run(
            step.command,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )
    duration = time.perf_counter() - start

    result = StepResult(
        step=step,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        duration_s=duration,
    )

    status_label = "PASS" if result.ok else "FAIL"
    status_style = "green" if result.ok else "red"
    console.print(f"[bold {status_style}]{status_label}[/bold {status_style}] in {duration:.2f}s")

    should_print_output = verbose or not result.ok
    if should_print_output:
        console.print()
        console.print(
            panel_cls(
                _format_output_block(result.stdout, width=console.width),
                title="stdout",
                border_style="blue",
                padding=(1, 2),
            )
        )
        console.print(
            panel_cls(
                _format_output_block(result.stderr, width=console.width),
                title="stderr",
                border_style="magenta",
                padding=(1, 2),
            )
        )

    return result


def _print_summary(console: Any, panel_cls: Any, table_cls: Any, target: str, results: Sequence[StepResult]) -> None:
    total = sum(r.duration_s for r in results)
    failures = [r for r in results if not r.ok]
    title_style = "green" if not failures else "red"
    title = f"{target} complete" if not failures else f"{target} failed"
    console.print()
    console.print(
        panel_cls(_wrap_block(title, width=console.width - 8), style=title_style, padding=(1, 2))
    )

    table = table_cls(show_header=True, header_style="bold", expand=True, padding=(0, 1))
    table.add_column("Step", ratio=3)
    table.add_column("Status", ratio=1)
    table.add_column("Time (s)", ratio=1, justify="right")
    for result in results:
        table.add_row(
            result.step.name,
            "[green]PASS[/green]" if result.ok else "[red]FAIL[/red]",
            f"{result.duration_s:.2f}",
        )
    table.add_row("Total", "-" if failures else "[green]PASS[/green]", f"{total:.2f}")
    console.print(table)


def _resolve_rich_types() -> dict[str, Any]:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Rich is required for pretty output. Run via "
            "`uv run --with rich python scripts/maintenance/pretty_make.py ...`."
        ) from exc
    return {"Console": Console, "Panel": Panel, "Table": Table, "Text": Text}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run common project checks with wrapped, high-signal rich text output.",
    )
    parser.add_argument(
        "target",
        choices=sorted(TARGET_STEPS),
        help="Pretty target name to execute.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Always print step stdout/stderr; otherwise only print output on failures.",
    )
    args = parser.parse_args()

    rich_types = _resolve_rich_types()
    console = rich_types["Console"](soft_wrap=True)
    panel_cls = rich_types["Panel"]
    table_cls = rich_types["Table"]
    text_cls = rich_types["Text"]
    target = args.target
    steps = TARGET_STEPS[target]

    intro = (
        "This mode improves readability with spacing, wrapped output, explicit step context, and timing. "
        "Use standard make targets in CI where raw logs are preferred."
    )
    console.print(
        panel_cls(
            _wrap_block(intro, width=console.width - 10),
            title=f"Inquira {target}",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    results: list[StepResult] = []
    for step in steps:
        result = _run_step(
            step,
            console=console,
            text_cls=text_cls,
            panel_cls=panel_cls,
            verbose=args.verbose,
        )
        results.append(result)
        if not result.ok:
            _print_summary(
                console,
                panel_cls=panel_cls,
                table_cls=table_cls,
                target=target,
                results=results,
            )
            return result.returncode

    _print_summary(
        console,
        panel_cls=panel_cls,
        table_cls=table_cls,
        target=target,
        results=results,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
