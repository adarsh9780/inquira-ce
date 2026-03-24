# Workspace Management

An AI analysis tool is only as useful as its ability to remember where you left off. Inquira CE relies on physical directory isolation and persistent local databases for 100% reliable workspace recovery.

## What is a Workspace?
When you start a new conversation or project, Inquira generates a dedicated, isolated `workspace` folder on your local hard drive. 
Think of a Workspace as a totally isolated sandbox containing:
- Its own `workspace.duckdb` Relational Database file
- A `meta/` directory for holding AI schema definitions
- A `staging/` directory for generated chart artifacts, downloaded exports, and intermediate steps

## Absolute Persistence
Because all imported tables and data are physically written to a dedicated DuckDB file inside the workspace folder, **your progress is immune to application closures or kernel crashes**.

If you import a 4GB Parquet file, analyze it with the agent, generate a Plotly chart, and then immediately shut down your computer—everything is saved. When you reopen Inquira CE and click on that historical chat, your workspace reloads instantly. You don't need to re-upload files or recalculate base aggregations.

## Session Isolation for Privacy
Every workspace is completely sandboxed from your other projects.
- **No crosstalk**: A Jupyter kernel running executed code in `Workspace A` cannot access the DuckDB connection or file paths from `Workspace B`.
- **Dedicated States**: The LangGraph Agent checkpoints are scoped precisely per-workspace. The AI Planner will never confuse instructions or context from a different project into your active one.

## Workspace Cleanup
If you explicitly choose to delete a conversation in the UI, Inquira CE executes a complete tear-down. The dedicated workspace directory is physically purged from your local hard drive alongside the chat logs, destroying the DuckDB caches and downloaded charts to instantly reclaim storage space.
