# Agent Protocol

## Commit & Testing Procedures

1. Always update the `commit_message` file in the root directory whenever a change is made.
2. Overwrite the file if the previous git commit message matches the current content of the `commit_message`; otherwise, append the new changes.
3. For every bug and feature we add or report, create a dedicated test case to prevent regressions.

## Environment & Communication

1. Use `uv` as the default package manager, falling back to `python3` or `python` if necessary.
2. If a requested change seems suboptimal, point it out and provide a rationale.
3. Always explain technical points in layman's terms with clear examples.
