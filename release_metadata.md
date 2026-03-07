Based on the commit history from the last release (`v0.5.7a6`) to the current state, here is a categorized summary of all the changes, features, and bug fixes that have been made:

### 🚀 New Features & Enhancements

**LLM & Provider Support**
- **Multi-Provider Support:** Added a multi-provider chat model factory with support for Ollama, OpenAI, and Anthropic.
- **Provider-Aware Configuration:** Implemented provider-aware LLM configurations, allowing per-provider API keys and distinct model catalogs.
- **`inquira.toml` Integration:** Now using `inquira.toml` as the primary source of truth for provider models.
- **UI Updates:** Added Gemma models to the UI and updated API settings dropdowns.

**Chat & UX**
- **Arrow-Key Recall:** Added the ability to recall recent user questions in the chat input using up/down arrow keys.
- **Chat History Redesign:** Restyled the shell renderer to a clean, light card design with status indicators.
- **Keyboard Shortcuts:** Added VS Code-style global keyboard shortcuts for the sidebar and terminal.
- **Execution Feedback:** Improved Shift+Enter execution feedback, preventing overlapping code runs.

**Schema & Data Exploration**
- **Editable Aliases:** Exposed editable schema aliases in the schema generator.
- **Hybrid Retrieval:** Switched the v2 agent to a hybrid schema retrieval mechanism with alias-aware search.
- **Schema Editor UI:** Modernized the schema editor UI, adding an in-tab dataset schema switcher.
- **EDA Slash Commands:** Implemented backend-driven Exploratory Data Analysis (EDA) slash commands alongside workspace-aware autocompletion.

**Agents & Workspace**
- **Agent V2 Scaffold:** Introduced a config-driven agent registry, v2 scaffold, and an intervention-ready SSE flow.
- **Persistence Spilt:** Split persistence into auth and appdata databases with principal-based ownership.
- **Output Routing:** Replaced the legacy Variable Explorer pane with a new Output pane that routes runtime logs (stdout/stderr) natively via SSE.
- **Timeline Inspector:** Redesigned the output pane as a timeline inspector and hardened right-panel memory behavior.

### 🐛 Bug Fixes

**Frontend & UI**
- **API Key Flags:** Synced store state from backend responses to fix stale API key requirement flags (fixing the Ollama API key bug).
- **Artifact Protection:** Guarded against stale artifact selection requests and gated artifact deletion on resolved confirmation.
- **Tables & Grids:** Restored AG Grid sort and search features for artifact tables.
- **Text Wrapping:** Automatically wrapped schema description and alias text.
- **Chat Scrolling:** Stopped scroll-to-bottom snapback after a user wheel/trackpad interaction, and ensured hydrated history opens at the latest message with contextual scroll-to-bottom controls.
- **Sidebar & Layout:** Eliminated sidebar close jerk interactions caused by header logo re-layouts.
- **Right Pane Syncing:** Persisted table/chart artifact selections across right-pane tab remounts and stabilized workspace UX by syncing artifact-driven panes.

**Backend & Runtime**
- **Database Safety:** Started using read-only DuckDB connections for slash commands and schema introspection.
- **Slash Commands:** Fixed support for spaced column references in commands, emitted DuckDB-safe quoted column references in autocomplete, and supported legacy bracket syntax. Command turns are now correctly persisted.
- **Suggest Dropdown Navigator:** Preserved arrow-key navigation in the autocomplete suggestion dropdown.
- **Dataframe Output Capturing:** Supported auto-capturing dataframe and figure outputs from arbitrary variable names, unifying artifact capture for manual and agent execution flows.
- **Auto-healing:** Moved workspace kernel bootstrap to a lazy dataset-triggered flow to self-heal missing workspace DBs.
- **Agent Recovery:** Regenerated analysis code defensively after runtime tool failures, hardening router serialization paths.
- **Release Automation:** Pinned the `uv` version across local and GitHub desktop release builds.

### 🧹 Chores & Other Changes
- **Legacy Cleanup:** Removed legacy startup artifacts for `chat_history.db` and `config.json`. Enforced v1-only fail-fast imports by completely removing the legacy `api`/`database` stack.
- **Agent Tuning:** Updated the agent's core instructions and added logic to automatically detect variables to display on the frontend.
- **Tauri Bundling:** Stopped bundling removed legacy backend paths.
