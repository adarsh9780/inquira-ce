# Copilot Instructions for Inquira-UI

## Project Overview

- **Inquira-UI** is a Vue.js 3 (Composition API) frontend for an AI-powered data analysis desktop app.
- The backend (not in this repo) is FastAPI (Python), communicating via REST endpoints.
- The app transforms natural language queries into Python/DuckDB code, executes them, and visualizes results.

## Architecture & Data Flow

- **Frontend**: Located in `src/`.
  - **Major UI Components**: `src/components/analysis/` (CodeTab, FigureTab, TableTab, TerminalTab, NotebookCell), `src/components/chat/`, `src/components/layout/`, `src/components/modals/`, `src/components/ui/`.
  - **State Management**: Pinia stores in `src/stores/` (e.g., `appStore.js`, `authStore.js`).
  - **Services**: API calls and data logic in `src/services/` (e.g., `apiService.js`, `factService.js`, `websocketService.js`).
  - **Composables**: Vue composition utilities in `src/composables/`.
  - **Assets**: Static files in `public/` and `src/assets/`.
- **External Communication**:
  - REST API endpoints (see README for details)
  - WebSocket for real-time updates (`websocketService.js`)
  - LLM integration via Google Gemini (API key required)

## Developer Workflows

- **Start Frontend**: `npm run dev` (Vite, port 5173)
- **Build Frontend**: `npm run build`
- **Run Frontend Tests**: `npm run test` (Vitest)
- **Backend**: Not present here; see README for setup and API endpoints.
- **Environment Variables**: Frontend config in `.env`, backend config in backend repo.

## Project-Specific Patterns

- **Component Structure**: Use Composition API and script setup syntax for new Vue components.
- **State**: Use Pinia for global state, avoid Vuex.
- **API Calls**: Centralize in `src/services/`, use async/await, handle errors with user toasts (`useToast.js`).
- **Modals**: All modal dialogs are in `src/components/modals/` and use a consistent props/events pattern.
- **Data Visualization**: Use Plotly.js for charts, AG Grid for tables.
- **Authentication**: Managed via `authStore.js` and `AuthModal.vue`.
- **Caching**: Use `cacheService.js` for local data caching.
- **Testing**: Use Vitest for frontend, pytest for backend (see README for commands).

## Integration Points

- **LLM API**: Requires Google Gemini API key, set via settings modal or `.env`.
- **Backend API**: All data, analysis, and export actions go through REST endpoints (see README for endpoint list).
- **WebSocket**: Used for progress updates and real-time feedback.

## Conventions & Examples

- **File Naming**: Use PascalCase for components, camelCase for JS files.
- **Error Handling**: Show user-friendly toasts for API errors.
- **Exports**: Support CSV, PNG, HTML export via backend endpoints.
- **Schema**: Optional schema files for data structure, see README for format.

## Key Files & Directories

- `src/components/analysis/`: Core analysis UI
- `src/services/apiService.js`: API logic
- `src/stores/appStore.js`: App-wide state
- `src/components/modals/`: Modal dialogs
- `src/composables/useToast.js`: Toast notifications
- `vite.config.js`: Vite config and proxy settings
- `README.md`: Full architecture, setup, and API docs

---

For backend details, see the main README and backend repo. For unclear patterns or missing conventions, ask for clarification or examples from the user.
