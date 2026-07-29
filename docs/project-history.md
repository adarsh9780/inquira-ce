# Project history

Inquira Community Edition is a continuing product, not a new application whose
history began with the Go rewrite.

The original Inquira CE repository was initialized on September 2, 2025. It
developed the local-first workspace, DuckDB, AI-assisted analysis, desktop
interface, packaging, release, and security foundations using Python, Vue, and
Tauri.

Work on the Go/Wails implementation began on July 16, 2026 as a separate Git
history so the native runtime could be designed and validated without
destabilizing the existing CE product. That implementation retained the product
goals and user experience while replacing the application service layer and
desktop shell.

On July 29, 2026, the two histories were joined with an explicit two-parent
merge commit:

- one parent preserves every commit reachable from the original CE `master`;
- the other parent preserves every commit reachable from the Go/Wails `main`;
- the merge tree is exactly the reviewed Go/Wails source tree;
- the original CE release tags remain available without being rewritten.

No legacy commits were rebased, squashed, or assigned artificial dates during
the migration. The retired Tauri/Python tree remains inspectable through Git
history and the archived `inquira-ce-legacy` repository, while current
development continues from the Go/Wails tree in `inquira-ce`.

This structure makes the product lineage auditable while keeping the active
codebase unambiguous.
