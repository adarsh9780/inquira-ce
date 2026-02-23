# Commit And Release Flow

Use Makefile targets from repo root.

## Preferred Commit Flow (Atomic Commands)

Prefer atomic commands so you can verify each step before the next one:

```bash
make check-version
make test
make git-add
make git-commit
make git-push
```

Why this flow is recommended:
- You can stop immediately when one step fails.
- Failures are easier to diagnose than in one-shot automation.
- It keeps commit/release hygiene predictable for the whole team.

Notes:
- `make git-commit` uses the root `commit_message.txt` file.
- Prefer this atomic flow over `make push` unless you are absolutely sure you want one-shot automation.

## Optional Release Flow

Only run this when preparing a release/tag.

1. Set a new version (must be strictly greater than current `VERSION`):
```bash
make set-version 0.5.0a7
```
This writes the version to `VERSION` and applies it across backend/frontend/tauri packaging files.

2. Update release metadata JSON from your local `release_metadata.md`:
```bash
make metadata
```
This generates `.github/release/metadata.json` used by the release workflow.

3. Commit and push (prefer atomic commands):
```bash
make test
make git-add
make git-commit
make git-push
```

4. Tag and publish release workflow:
```bash
make git-tag
```

`release_metadata.md` format:
- First non-empty line: release title (markdown heading is allowed).
- Remaining content: release body.

Next: [CI And Release Automation](./ci-and-release-automation.md)
