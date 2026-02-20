# 🚀 Inquira - AI-Powered Data Analysis Tool

<p align="center">
  <img src="./src/inquira/logo/inquira_logo.svg" alt="Inquira Logo" width="100" height="100">
</p>

<p align="center">
  <strong>Transform natural language into powerful data insights with AI-generated Python code</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Version-0.4.6a0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

---

**Inquira** is a local-first desktop application that functions as an autonomous data analyst. It allows you to load datasets (CSV, Excel, Parquet, DuckDB) and ask natural language questions. The AI plans the analysis, writes and executes Python/DuckDB code locally, and renders interactive results.

## ⚡ Quick Start

### Option 1: Zero-Install (Run instantly)
Requires **curl** (macOS/Linux) or **PowerShell** (Windows). No pre-installed Python required.

**macOS/Linux**:
```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/run-inquira.sh | bash
```

**Windows**:
```powershell
irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/run-inquira.ps1 | iex
```

### Option 2: Install Locally
Adds `inquira` to your PATH.

**macOS/Linux**:
```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.sh | bash
# Then run:
inquira
```

---

## 🛠️ Development Setup

If you want to contribute or build from source:

### Prerequisites
*   **Python 3.12+**
*   **UV** (Python package manager)
*   **Node.js 18+** (Only if modifying the frontend)

### 1. Backend Setup
```bash
git clone https://github.com/adarsh9780/inquira-ce.git
cd inquira-ce/backend
uv sync
uv run python main.py
```
The app will start at `http://localhost:8000/ui`.

### 2. Frontend Setup (Optional)
The backend includes pre-built frontend assets in `backend/app/frontend/dist`. To modify the UI:

1.  Navigate to `frontend/`.
2.  Install & Run:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
3.  Link to backend:
    ```bash
    # In backend terminal
    export INQUIRA_DEV_UI_DIR=$(pwd)/../frontend/dist
    uv run python main.py
    ```

---

## ⚙️ Configuration

Configure via UI (**Settings**) or environment variables (`.env`).

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Your Gemini API Key | None |
| `INQUIRA_ALLOW_FILE_DIALOG` | Enable native file picker | `1` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## ✨ Features

*   **Local Execution**: Code runs on your machine, not the cloud.
*   **Multi-Format**: Support for CSV, Excel, Parquet, and DuckDB.
*   **AI-Powered**: Uses Google Gemini for code generation.
*   **Visualizations**: Auto-generates interactive Plotly charts.
*   **Project Aware**: Persistent sessions and file-based schemas.

---

## 🎯 Roadmap & Enhancements

#### **Immediate Technical Debt**
- [ ] **Testing**: Add a comprehensive test suite (pytest) for the agent logic and prompt rendering.
- [ ] **Error Handling**: Implement strict timeouts for code execution and graceful degradation when the LLM fails to plan.
- [ ] **CI/CD**: Set up GitHub Actions for automated testing and linting.

#### **Future Features**
- [ ] **Mobile App** (React Native)
- [ ] **Cloud Deployment** (AWS/GCP)
- [ ] **Team Collaboration** features
- [ ] **Advanced ML** integrations
- [ ] **Plugin System** for custom analyses

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
