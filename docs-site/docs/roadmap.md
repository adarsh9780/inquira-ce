# Roadmap

As Inquira CE moves from its Beta testing phase into long-term stability, our development pipeline is deeply focused on robust security, data scale, and advanced analytical capabilities.

Below is our active roadmap based on the current codebase state and community priorities.

## Near-Term Priorities

### 1) Authentication & Onboarding
- **Frictionless Onboarding:** Completely remove mandatory login requirements for all local workflows to ensure an open, instant-start experience.
- **Opt-In Telemetry:** Build a transparent, optional analytics modal during the first-time application setup to securely catch crash reports and improve execution stability.

### 2) Security & Architecture
- **Sandboxed Execution:** Introduce robust OS or Tauri-level sandboxing (e.g., investigating NVIDIA Open Shell compatibility) for the Python executor to guarantee local security protocols.
- **Settings Management:** Clean up local `inquira.toml` config dependencies and expose configuration toggles directly inside the workspace UI.
- **OAuth Integrations:** Exploring how to use existing OAuth tokens for direct model access (e.g., Codex, Antigravity). Note: Anthropic does not natively allow this flow, so it is not currently prioritized for their models.

### 3) Data & Execution Reliability
- **Code Persistence:** Persist generated code state directly to a physical Python script (enforcing a strict `1 workspace = 1 code file` architecture).
- **Large Image Optimization:** Stream base64 image outputs dynamically when chart payload sizes cross performance thresholds UI stability.
- **Table View Caching:** Memory-cache pagination offsets and limits for massive data tables to drastically improve scrolling and data-grid performance.
- **Native Contexts:** Enable direct attachments and operations on raw DuckDB (`.duckdb`) files.

---

## Future Explorations (Active Pipeline)

While the core focus remains on the local SQL/DuckDB pipelines, we are actively scoping out advanced features to handle more complex enterprise workflows and unstructured data:

- **Advanced Retrieval-Augmented Generation (RAG):** Explore architectures to natively ingest and chat with PDFs, text documents, and unstructured data alongside your existing relational SQL tables.
- **Model Context Protocol (MCP):** Allow the internal LangGraph agent to interface dynamically with external local tools, file systems, or custom APIs.
- **Enterprise-Grade Data Connectors:** Build dedicated, high-speed connections to centralized Data Lakes and Warehouses (e.g., Snowflake, BigQuery, Databricks).
- **Fine-Grained Access Control:** Outline Role-Based Access Control logic for secure, multi-user deployments.
