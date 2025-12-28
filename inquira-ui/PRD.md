# Product Requirements Document

## 1. Product Summary

**Purpose**
A natural-language data analysis assistant that generates and executes Python code locally against user-provided datasets. It returns results as tables, charts, and explanations.

**Platforms**

- Web (local backend)
- Near-term desktop target using **Tauri** (to simplify file access and remove filesystem path friction).

**MVP Scope**

- Local files only.
- Schema generation required (upload optional).
- Gemini as default LLM with provider abstraction for LiteLLM/OpenRouter.
- Secure-enough local code execution sandbox.
- Single-user workflows (no collaboration).

**Out of Scope**

- Cloud data sources, collaboration/sharing, enterprise governance, fine-grained RBAC, version control/notebook features.

---

## 2. Personas

### **Data Analyst**

- Comfortable with CSV/Excel.
- Wants quick insights without manual coding.
- Appreciates downloadable Python code for **auditability and reproducibility**.

### **Non-Technical User (Ops/PM)**

- Asks domain-specific questions in plain English.
- Expects simple, clear answers (tables, charts, or explanations).
- Requires minimal setup and friction.

---

## 3. Goals

- **Fast question-to-insight loop** with generated Python code.
- **Schema generation required** to improve LLM code quality (upload optional).
- **Local-only execution** — no data leaves the user’s machine.
- **Model choice abstraction** (Gemini now, LiteLLM/OpenRouter later).
- **Safe-enough code execution** with clear outputs: tables, charts, logs.
- **Downloadable code** and basic undo/redo in editor.

---

## 4. Key User Stories

- As a user, I set my **API key** and **local data path(s)**.
- As a user, I generate a **schema** (or upload one) for better analysis.
- As a user, I ask a **question** and receive:

  - Generated Python code
  - Plain-language explanation
  - A result table or chart

- As a user, I can **run code safely**, view terminal output, and undo changes.
- As a user, I can **download Python code** for reuse.
- As a user, I can preview **data samples** (first N rows or random).
- As a user, I can switch **models** without changing workflows.

---

## 5. Core Flows

### **Setup**

1. Open app → authenticate (local).
2. Enter API key.
3. Set data file path(s).
4. Generate schema (required) or upload schema (optional).

### **Q\&A**

1. User asks a question.
2. Backend builds instruction (schema + context + data path).
3. LLM returns JSON: `{is_safe, is_relevant, code, explanation}`.
4. UI saves code, displays results in correct tab (table/figure/terminal).

### **Code Run**

- User runs code → backend executes safely.
- UI renders:

  - **Table**: AG Grid (from `result_df`).
  - **Chart**: Plotly (from `figure`).
  - **Terminal logs/errors**.

### **Schema**

- Backend generates schema from data file.
- Users can refine or upload schema JSON.
- Schema is persisted locally.

---

## 6. System Overview

### **Frontend (Vue + Pinia)**

- Chat input & history.
- Code editor (CodeMirror6) with undo/redo.
- Output tabs:

  - **Table** (AG Grid)
  - **Chart** (Plotly JSON)
  - **Terminal logs**

- Settings modal: model, API key, paths, schema.
- Local persistence: `localStorage`.

### **Backend (FastAPI - “Inquira”)**

- Auth/session endpoints.
- Settings management.
- Chat/LLM service.
- Code execution sandbox.
- Schema generation & preview endpoints.
- API key management.

### **Data Handling**

- User provides **absolute file paths**.
- No browser file picker (due to web sandbox).
- All data processing remains **local**.
- Schema stored as JSON.

---

## 7. Functional Requirements

### **Authentication**

- Local cookie-based sessions.
- Settings retrieval per user.

### **Settings**

- Store API key, model, data path, schema path, schema context.
- Validate API key presence.
- Schema required (upload optional).

### **Schema**

- Generate schema from data files.
- Save/load JSON schema.

### **Chat & Code Generation**

- Enforce `is_safe` and `is_relevant`.
- Templates must embed schema + context.
- Use **DuckDB → Pandas** pipeline.
- Always define `result_df` and (optional) `figure`.

### **Code Execution**

- AST analysis for unsafe patterns.
- Execute in restricted environment (no network, timeout).
- Capture stdout/stderr, variables, execution time.

### **Editor**

- Single session file.
- Auto-save in state store.
- Undo/redo support.
- Download `.py` file.

### **Data Preview**

- Random sample or first-N rows via DuckDB.

### **Model Selection**

- Default Gemini.
- Provider abstraction for LiteLLM/OpenRouter.

---

## 8. Non-Functional Requirements

- **Performance**: Sub-3s UI interactions.
- **Security**: Sandbox execution, deny unsafe AST, block network egress.
- **Privacy**: No data leaves machine, keys stored locally.
- **Reliability**: Preserve code/settings across sessions, graceful error handling.

---

## 9. UX Requirements

- Clear status indicators (API key, schema required).
- Tabbed results with keyboard shortcuts (1–4).
- Settings modal as central entry point.
- Explanations rendered as Markdown.
- Copy & download actions for code and results.
- Undo/redo (keyboard + small UI affordance).

---

## 10. Integrations

### **LLM Provider Abstraction**

- Interface: send structured prompt → receive structured JSON.
- Default: Gemini.
- Future: LiteLLM/OpenRouter.

### **Data Engines**

- DuckDB for projection/filtering.
- Pandas for shaping.
- Plotly for visualizations.

---

## 11. Desktop Roadmap (Tauri)

- Native file/directory picker.
- Persist local workspace.
- Secure sandbox (WASM/permissions).
- OS keychain for API keys.

---

## 12. Release Plan

### **MVP (Web + Local Backend)**

- Required schema generation.
- Q\&A flow → code → safe run → results.
- Code download (.py).
- Undo/redo in editor.
- Model selector (Gemini only).

### **Next Iterations**

- LiteLLM/OpenRouter integration.
- Enhanced data preview (column stats).
- Desktop packaging (Tauri).
- Local code revision history.

---

## 13. Success Metrics

- **Time to first insight** (open → first valid chart/table).
- **Code acceptance rate** (runs without modification).
- **Error rate** (AST violations, runtime errors).
- **Code downloads** frequency.
- **Schema adoption rate** (gen vs. upload).
- **Clarity of explanations** (user-reported).

---

## 14. Open Questions

- **Chat history**: Keep per-session transient or store with timestamps/code links?
- **Code revisions**: Basic undo vs. visible revision timeline?
- **Sandbox packages**: Which Python libs are allowed (duckdb, pandas, plotly pinned)?
