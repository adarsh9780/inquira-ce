# 🚀 Inquira - AI-Powered Data Analysis Tool

<p align="center">
  <img src="./logo/inquira_logo.svg" alt="Inquira Logo" width="100" height="100">
</p>

<p align="center">
  <strong>Transform natural language into powerful data insights with AI-generated Python code</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Version-0.3.1-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue.js-3-4FC08D?style=for-the-badge&logo=vue.js" alt="Vue.js">
  <img src="https://img.shields.io/badge/FastAPI-00C853?style=for-the-badge&logo=fastapi" alt="FastAPI">
</p>

---

## ⚡ Quick Install

macOS/Linux (install once):

```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.sh | bash
```

Windows PowerShell (install once):

```powershell
irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.ps1 | iex
```

Run without installing (one-off):

- macOS/Linux: `curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/run-inquira.sh | bash`
- Windows PowerShell: `irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/run-inquira.ps1 | iex`

Notes:
- No system Python required; `uv` installs automatically and fetches Python 3.12 if needed.
- To pin a different release wheel, set `INQUIRA_WHEEL_URL` before running.
- On Windows, if script execution is restricted, run: `Set-ExecutionPolicy -Scope Process Bypass -Force`

## ▶️ Usage

After installation, start Inquira from any terminal:

```bash
inquira
```

What happens:
- Starts the FastAPI backend at `http://localhost:8000` and opens the UI at `/ui`.
- First time usage: set your LLM API key in Settings.
- Upload a dataset (CSV/Excel/Parquet/DuckDB) and start asking questions.

## 📋 Table of Contents

- [🎯 What is Inquira?](#-what-is-inquira)
- [💡 Value Proposition](#-value-proposition)
- [👥 Target Audience](#-target-audience)
- [✨ Key Features](#-key-features)
- [🚀 Quick Start](#-quick-start)
- [📖 How to Use](#-how-to-use)
- [🛠️ Technical Architecture](#️-technical-architecture)
- [🔧 Installation & Setup](#-installation--setup)
- [📚 API Documentation](#-api-documentation)
- [⚙️ Configuration](#️-configuration)
- [🔒 Security](#-security)
- [🐛 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🙋 Support](#-support)

---

## 🎯 What is Inquira?

**Inquira** is a revolutionary desktop application that democratizes data analysis by allowing users to query structured data using natural language. Powered by advanced Large Language Models (LLMs), Inquira automatically generates, executes, and visualizes Python code based on your questions.

### 🎪 How It Works

1. **Ask in Plain English**: "Show me sales by category this quarter"
2. **AI Generates Code**: LLM creates optimized Python/DuckDB queries
3. **Instant Execution**: Code runs automatically with real-time results
4. **Visual Insights**: Interactive charts, tables, and exports

### 🏆 Core Capabilities

- **📊 Multi-Format Support**: CSV, Excel, Parquet, DuckDB databases
- **🤖 AI-Powered**: Google Gemini integration for intelligent code generation
- **🎨 Rich Visualizations**: Plotly charts and interactive dashboards
- **⚡ Real-Time Execution**: Instant results with progress tracking
- **💾 Smart Caching**: Optimized performance for large datasets
- **🔄 Export Ready**: CSV, PNG, HTML export capabilities

---

## 💡 Value Proposition

### 🎯 **For Data Analysts & Scientists**
- **10x Faster Analysis**: Natural language queries instead of complex SQL/Python
- **Reduced Errors**: AI-generated code is optimized and tested
- **Focus on Insights**: Spend less time coding, more time analyzing

### 🏢 **For Business Users**
- **Self-Service Analytics**: No technical expertise required
- **Instant Answers**: Get insights in seconds, not hours
- **Cost Effective**: Reduce dependency on expensive analysts

### 🏫 **For Educators & Students**
- **Learn by Doing**: See how data analysis works in real-time
- **Interactive Learning**: Experiment with data without coding barriers
- **Practical Skills**: Understand both questions and solutions

### 💼 **For Organizations**
- **Democratize Data**: Enable non-technical users to explore data
- **Accelerate Decisions**: Faster insights drive better business outcomes
- **Reduce Costs**: Lower technical barriers to data access

---

## 👥 Target Audience

### 👨‍💼 **Primary Users**
- **Data Analysts** seeking faster workflows
- **Business Intelligence Teams** needing quick insights
- **Product Managers** exploring user behavior data
- **Marketing Teams** analyzing campaign performance
- **Financial Analysts** processing transaction data

### 👩‍🎓 **Secondary Users**
- **Students** learning data analysis concepts
- **Educators** teaching data science courses
- **Researchers** exploring datasets
- **Consultants** delivering client insights
- **Small Business Owners** understanding their data

### 🏢 **Enterprise Use Cases**
- **Retail**: Customer behavior analysis
- **Finance**: Transaction pattern detection
- **Healthcare**: Patient data insights
- **E-commerce**: Sales trend analysis
- **Logistics**: Supply chain optimization

---

## ✨ Key Features

### 🔍 **Data Analysis**
- ✅ Natural language to SQL/Python conversion
- ✅ Support for complex joins and aggregations
- ✅ Real-time query execution and results
- ✅ Interactive data exploration

### 📊 **Visualization**
- ✅ Automatic chart generation (bar, line, pie, scatter)
- ✅ Interactive Plotly visualizations
- ✅ Customizable chart themes and layouts
- ✅ Export charts as PNG/HTML

### 🎨 **User Interface**
- ✅ Modern, intuitive desktop application
- ✅ Dark/light theme support
- ✅ Drag-and-drop file uploads
- ✅ Real-time progress indicators

### 🔧 **Developer Experience**
- ✅ RESTful API for integrations
- ✅ Comprehensive logging and debugging
- ✅ Extensible plugin architecture
- ✅ Cross-platform compatibility

---

## 🚀 Quick Start

### 📋 Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.12+
- **UV** (Python package manager)
- **Google Gemini API Key**

### ⚡ 3-Step Setup

```bash
# 1. Clone and install frontend
git clone https://github.com/your-org/inquira.git
cd inquira
npm install

# 2. Setup backend
cd inquira  # Backend directory
uv sync

# 3. Start development servers
# Terminal 1: Backend
uv run python -m src.inquira.main

# Terminal 2: Frontend
npm run dev
```

**🎉 Ready!** Open `http://localhost:5173` and start analyzing data.

---

## 📖 How to Use

### 📤 **Step 1: Upload Your Data**
```bash
# Supported formats:
# - CSV files (.csv)
# - Excel files (.xlsx)
# - Parquet files (.parquet)
# - DuckDB databases (.db)
```

### 📝 **Step 2: Define Your Schema** (Optional)
Create a schema file describing your data structure:

```csv
Table Name,Column Name,Data Type,Description,Categories
sales_data,product_id,int,Unique identifier for products,
sales_data,product_name,string,Name of the product,
sales_data,category,string,Product category,"Electronics,Clothing,Books"
```

### 🔑 **Step 3: Configure API**
1. Get your [Google Gemini API key](https://makersuite.google.com/app/apikey)
2. Select your preferred model (gemini-pro, gemini-1.5-flash, etc.)
3. Enter your API key in the settings

### 💬 **Step 4: Ask Questions**
```bash
# Examples of natural language queries:

"Show me total sales by category this month"
"What are the top 10 best-selling products?"
"Compare sales performance across different regions"
"Find customers who haven't purchased in 30 days"
"Calculate average order value by customer segment"
```

### 📊 **Step 5: Review & Execute**
1. **Review Generated Code**: AI creates optimized Python/DuckDB code
2. **Execute Analysis**: Click run to see results instantly
3. **Explore Visualizations**: View charts and interactive dashboards
4. **Export Results**: Download data as CSV or charts as images

### 🎯 **Example Workflow**

```bash
# Upload: sales_data.csv (1M rows)
# Schema: sales_schema.csv
# Question: "What's the sales trend by category over the last 6 months?"

# Result: AI generates optimized query + beautiful visualization
```

---

## 🛠️ Technical Architecture

### 🏗️ **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vue.js 3      │    │   FastAPI       │    │   Google Gemini │
│   Frontend      │◄──►│   Backend       │◄──►│   LLM Service   │
│                 │    │                 │    │                 │
│ • Monaco Editor │    │ • Data Processing│    │ • Code Generation│
│ • AG Grid       │    │ • File Upload    │    │ • Query Optimization│
│ • Plotly Charts │    │ • Code Execution │    │ • Error Handling │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Data Sources  │
                       │                 │
                       │ • CSV/Excel     │
                       │ • Parquet       │
                       │ • DuckDB        │
                       │ • Local Files   │
└─────────────────┘
```

### 🛠️ **Technology Stack**

#### **Frontend**
- **Framework**: Vue.js 3 (Composition API)
- **Styling**: Tailwind CSS
- **Code Editor**: Monaco Editor (VS Code engine)
- **Data Grid**: AG Grid
- **Charts**: Plotly.js
- **Icons**: Heroicons
- **Build Tool**: Vite

#### **Backend**
- **Framework**: FastAPI (async Python)
- **Data Processing**: Pandas + DuckDB
- **LLM Integration**: Google Gemini API
- **File Handling**: aiofiles
- **Validation**: Pydantic
- **Package Manager**: UV

#### **Infrastructure**
- **Packaging**: PyInstaller (desktop app)
- **Database**: DuckDB (analytical queries)
- **Caching**: In-memory with file persistence
- **Logging**: Structured JSON logging

### 📊 **Performance Characteristics**

| Metric | Value | Notes |
|--------|-------|-------|
| **Query Response Time** | < 3 seconds | Average for typical queries |
| **Data Processing** | Up to 10M rows | Memory-optimized |
| **Concurrent Users** | 1 (desktop) | Single-user application |
| **File Size Limit** | 100MB | Configurable |
| **Code Execution Timeout** | 30 seconds | Configurable |

---

## 🔧 Installation & Setup

### ✅ Install Once (adds `inquira` to PATH)

macOS/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.sh | bash
# then in a new terminal
inquira
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.ps1 | iex
# then open a new terminal
inquira
```

Notes:
- The shim uses a released wheel by default: v0.4.2‑alpha.
- Override the source by setting `INQUIRA_WHEEL_URL` before running `inquira`.
- No system Python is required; uv fetches a Python 3.12 runtime as needed.

### 🟢 Option 0: Zero‑Install (curl | bash / irm)

Run Inquira without preinstalling Python. The bootstrap script installs uv, fetches a Python 3.12 runtime if needed, and executes the `inquira` CLI from the released wheel artifact.

macOS/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/run-inquira.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/run-inquira.ps1 | iex
```

Notes:
- The scripts default to the v0.4.2-alpha wheel: `https://github.com/adarsh9780/inquira-ce/releases/download/v0.4.2-alpha/inquira_ce-0.4.2-py3-none-any.whl`. Override with `INQUIRA_WHEEL_URL` if needed.
- When the package is published to PyPI, the scripts can be switched to `--from inquira-ce[==version]`.
- uv downloads an isolated CPython 3.12 if you don’t have Python installed.
- Behind a proxy, ensure your shell respects proxy env vars before running.

### 📦 **Option 1: Development Setup**

#### **Prerequisites**
- Node.js 18+ and npm
- Python 3.12+
- UV package manager
- Google Gemini API key

#### **Step-by-Step Installation**

```bash
# 1. Clone repository
git clone https://github.com/your-org/inquira.git
cd inquira

# 2. Frontend setup
npm install
npm run dev  # Starts at http://localhost:5173

# 3. Backend setup (new terminal)
cd inquira  # Navigate to backend directory
uv sync
uv run python -m src.inquira.main  # Starts at http://localhost:8000
```

### 🖥️ **Option 2: Desktop Application**

```bash
# Build for your platform
npm run build
cd inquira
uv run python -m src.inquira.build

# Find executable in dist/ directory
```

### 🐳 **Option 3: Docker Deployment**

```bash
# Build and run with Docker
docker build -t inquira .
docker run -p 5173:5173 -p 8000:8000 inquira
```

---

## 📚 API Documentation

### 🔗 **Core Endpoints**

#### **File Management**
```http
POST   /upload/data     # Upload data files
POST   /upload/schema   # Upload schema files
DELETE /upload/data/{id}    # Delete data file
DELETE /upload/schema/{id}  # Delete schema file
```

#### **Analysis Engine**
```http
POST   /analyze         # Generate code from natural language
POST   /execute         # Execute generated code
GET    /health          # Health check
```

#### **Export & Logging**
```http
POST   /export/csv      # Export data as CSV
POST   /export/chart    # Export chart as PNG/HTML
POST   /log/question    # Log user questions
GET    /log/questions   # Retrieve question history
```

### 📝 **Example API Usage**

```python
import requests

# Analyze data with natural language
response = requests.post('http://localhost:8000/analyze', json={
    'question': 'Show me sales by category',
    'data_file': 'sales.csv',
    'schema_file': 'schema.csv',
    'model': 'gemini-pro'
})

# Execute generated code
result = requests.post('http://localhost:8000/execute', json={
    'code': response.json()['code'],
    'data_file': 'sales.csv'
})
```

---

## ⚙️ Configuration

### 🔧 **Environment Variables**

Create `.env` file in backend directory:

```env
# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# File Handling
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=csv,xlsx,xls,parquet,db

# LLM Configuration
GEMINI_API_KEY=your_api_key_here
DEFAULT_MODEL=gemini-1.5-flash
CODE_TIMEOUT=30

# Security
SECRET_KEY=your_secret_key
CORS_ORIGINS=http://localhost:5173

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
```

### 🤖 **Supported LLM Models**

| Model | Context Window | Best For |
|-------|----------------|----------|
| `gemini-pro` | 32K tokens | General analysis |
| `gemini-1.5-flash` | 1M tokens | Large datasets |
| `gemini-1.5-pro` | 1M tokens | Complex analysis |
| `gemini-pro-vision` | 16K + images | Visual data |

---

## 🔒 Security

### 🛡️ **Security Features**

- **🔐 API Key Protection**: Keys never stored permanently
- **📁 File Validation**: Strict file type and size validation
- **⚡ Sandboxed Execution**: Limited Python imports and execution
- **🚫 No Cloud Storage**: All data remains local
- **🔍 Input Sanitization**: All user inputs validated
- **⏰ Execution Timeouts**: Prevents infinite loops
- **📊 Audit Logging**: Complete activity tracking

### ⚠️ **Security Best Practices**

1. **API Keys**: Rotate regularly, use restricted keys
2. **File Uploads**: Validate file types and scan for malware
3. **Network**: Use HTTPS in production
4. **Data**: Encrypt sensitive data at rest
5. **Access**: Implement user authentication if needed

---

## 🐛 Troubleshooting

### 🔧 **Common Issues & Solutions**

#### **1. Import Errors**
```bash
# Solution: Reinstall dependencies
cd inquira
uv sync --reinstall
```

#### **2. Port Conflicts**
```bash
# Change ports in .env
API_PORT=8001
# Frontend proxy in vite.config.js
target: 'http://localhost:8001'
```

#### **3. API Key Issues**
```bash
# Check API key validity
curl -H "Authorization: Bearer YOUR_KEY" \
     https://generativelanguage.googleapis.com/v1/models
```

#### **4. Memory / Large Files**
- DuckDB connections are capped at ~500MB memory with on‑disk spill to avoid loading entire files.
- `.xlsx` uses DuckDB excel extension when available; `.xls` is not supported. Convert `.xls` to `.xlsx` or `.csv`.

#### **5. Code Execution Timeouts**
```env
# Increase timeout in .env
CODE_TIMEOUT=60
```

### 📊 **Performance Tuning**

```python
# Optimize for large datasets
df = pd.read_csv('large_file.csv', chunksize=10000)
for chunk in df:
    # Process in chunks
    pass
```

### 🔍 **Debug Mode**

```bash
# Enable detailed logging
export DEBUG=True
export LOG_LEVEL=DEBUG

# Check logs
tail -f logs/inquira.log
```

---

## 🤝 Contributing

### 🚀 **Development Workflow**

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature/amazing-feature`
3. **Install** dependencies: `npm install && uv sync`
4. **Make** changes with tests
5. **Commit**: `git commit -m 'Add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Create** Pull Request

### 📋 **Code Standards**

- **Frontend**: Vue 3 Composition API, TypeScript preferred
- **Backend**: FastAPI with Pydantic models
- **Testing**: pytest for backend, Vitest for frontend
- **Documentation**: Update README for new features
- **Commits**: Conventional commit format

### 🧪 **Testing**

```bash
# Frontend tests
npm run test

# Backend tests
uv run pytest

# End-to-end tests
npm run test:e2e
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Inquira

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

---

## 🙋 Support

### 📞 **Getting Help**

- **📧 Email**: support@inquira.dev
- **💬 Discord**: [Join our community](https://discord.gg/inquira)
- **📖 Documentation**: [Full docs](https://docs.inquira.dev)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/your-org/inquira/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/your-org/inquira/discussions)

### 📚 **Resources**

- **🖥️ Live Demo**: [Try Inquira](https://demo.inquira.dev)
- **📺 Tutorials**: [YouTube Channel](https://youtube.com/@inquira)
- **📝 Blog**: [Latest Updates](https://blog.inquira.dev)
- **📰 Newsletter**: [Stay Updated](https://newsletter.inquira.dev)

### 🎯 **Roadmap**

- [ ] **Mobile App** (React Native)
- [ ] **Cloud Deployment** (AWS/GCP)
- [ ] **Team Collaboration** features
- [ ] **Advanced ML** integrations
- [ ] **Plugin System** for custom analyses

---

<p align="center">
  <strong>Made with ❤️ for data enthusiasts worldwide</strong>
</p>

<p align="center">
  <a href="https://github.com/your-org/inquira">⭐ Star us on GitHub</a> •
  <a href="https://twitter.com/inquira_dev">🐦 Follow on Twitter</a> •
  <a href="https://discord.gg/inquira">💬 Join Discord</a>
</p>

## Features

- **Data Input**: Support for CSV, Excel, Parquet, and DuckDB files
- **Schema Definition**: Upload schema files to describe your data structure
- **LLM Integration**: Uses Google Gemini models for code generation
- **Interactive Analysis**: IDE-like interface with editable, executable code
- **Visualizations**: Generate Plotly charts and graphs
- **Data Export**: Export results as CSV or charts as images
- **Logging**: Track all user questions locally
- **Desktop App**: Can be packaged as a standalone desktop application

## Architecture

- **Frontend**: Vue.js 3 + Tailwind CSS + Monaco Editor + AG Grid + Plotly
- **Backend**: FastAPI + Python 3.12+
- **Data Processing**: Pandas + DuckDB
- **LLM**: Google Gemini API
- **Packaging**: PyInstaller for desktop distribution

## How Ingestion Works (Behind the Scenes)

When you point Inquira at a data file, it performs a few background steps to make analysis fast and repeatable:

- File fingerprinting: Inquira computes a stable fingerprint (MD5) of the file using its normalized path, size, and modified time. This identifies a specific file/version without reading the entire content.
- DuckDB conversion with stable table names: The file is imported into a persistent DuckDB database under a stable table name derived from the filename (non-alphanumeric replaced with underscores, forced lowercase, and prefixed with `t_` if needed). If the file fingerprint changes (the file is edited or replaced), Inquira overwrites the same table name with the new data.
- Per-file schemas: Inquira generates a schema JSON for each unique file fingerprint and stores it at `~/.inquira/{user_id}/schemas/{user_id}_{fingerprint}_schema.json`. If the file changes, a new schema is generated for the new fingerprint. Stored file metadata helps ensure schemas are fresh.
- Dataset catalog: Inquira maintains a datasets catalog in SQLite at `~/.inquira/inquira.db` (table `datasets`) that tracks `user_id, file_path, file_hash, table_name, schema_path, file_size, source_mtime`.

Notes and implications:
- Changing a file in place (same path) updates the existing DuckDB table’s contents.
- Moving/renaming a file produces a different fingerprint and will be treated as a new dataset.
- Legacy behavior (a single schema per user) is supported for migration, but new schemas are per-file fingerprint.

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.12+
- UV (Python package manager)

### Frontend Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup

```bash
# Navigate to backend directory
cd inquira

# Install dependencies (UV will create virtual environment automatically)
uv sync

# Start the FastAPI server
uv run python src/inquira/main.py
```

The backend API will be available at `http://localhost:8000`

### Full Development Mode

1. Start the backend server:

```bash
cd inquira
uv run python -m src.inquira.main
```

2. In a new terminal, start the frontend:

```bash
npm run dev
```

3. Open `http://localhost:5173` in your browser

The Vite dev server will proxy API calls to the FastAPI backend.

## API Endpoints

### File Upload

- `POST /upload/data` - Upload data files (CSV, Excel, Parquet, DuckDB)
- `POST /upload/schema` - Upload schema files (CSV, Excel)
- `DELETE /upload/data/{file_id}` - Delete uploaded data file
- `DELETE /upload/schema/{file_id}` - Delete uploaded schema file

### Analysis

- `POST /analyze` - Generate Python code using LLM
- `POST /execute` - Execute Python code and return results

### Export

- `POST /export/csv` - Export data as CSV
- `POST /export/chart` - Export chart as PNG/HTML

### Logging

- `POST /log/question` - Log user questions
- `GET /log/questions` - Retrieve logged questions
- `GET /log/stats` - Get logging statistics

### Health

- `GET /health` - Health check endpoint

## Usage

1. **Upload Data**: Choose your data file (CSV, Excel, Parquet, or DuckDB)
2. **Upload Schema**: Provide a schema file describing your data structure
3. **Configure LLM**: Select a Gemini model and enter your API key
4. **Ask Questions**: Type natural language questions about your data
5. **Review Code**: Examine the generated Python code
6. **Execute & Analyze**: Run the code to see results, tables, and charts
7. **Export Results**: Download data as CSV or charts as images

## Schema File Format

Your schema file should be a CSV or Excel file with these columns:

| Column Name | Description                                         |
| ----------- | --------------------------------------------------- |
| Table Name  | Name of the data table                              |
| Column Name | Name of the column                                  |
| Data Type   | Data type (int, string, float, date, datetime)      |
| Description | Description of what the column contains (mandatory) |
| Categories  | Optional: comma-separated list of possible values   |

Example:

```csv
Table Name,Column Name,Data Type,Description,Categories
sales_data,product_id,int,Unique identifier for products,
sales_data,product_name,string,Name of the product,
sales_data,category,string,Product category,"Electronics,Clothing,Books"
sales_data,price,float,Price in USD,
sales_data,sale_date,date,Date of sale,
```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
UPLOAD_DIR=uploads
LOG_DIR=logs
MAX_FILE_SIZE=104857600
CODE_TIMEOUT=30
```

### Supported Models

- gemini-pro
- gemini-pro-vision
- gemini-1.5-pro
- gemini-1.5-flash

## Security Considerations

- Code execution is sandboxed with limited imports
- File uploads are validated and size-limited
- API keys are not stored permanently
- Local logging only (no cloud storage)

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure all dependencies are installed with `uv sync`
2. **Port conflicts**: Change ports in configuration if 8000/5173 are in use
3. **API key issues**: Verify your Gemini API key is valid and has quota
4. **File upload failures**: Check file size limits and supported formats
5. **Code execution timeouts**: Increase `CODE_TIMEOUT` for complex operations

### Development Tips

- Use the browser developer tools to debug frontend issues
- Check FastAPI logs for backend errors
- Test API endpoints directly at `http://localhost:8000/docs`
- Monitor file uploads in the `uploads/` directory
- Check question logs in the `logs/` directory

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
#### **Settings & Rebuild Checks**

- `GET /settings/view` – Merged settings + paths + file metadata (size, mtime/ctime) + dataset info (`table_name`, timestamps). Also returns a derived table name if the dataset hasn’t been created yet.
- `GET /settings/check-update` – Non‑mutating check for whether a rebuild is needed. Reasons may include: `no_dataset_entry`, `source_missing`, `mtime_newer`, `size_changed`, `table_missing`.
- `PUT /settings/set/data_path` – Saves the path and triggers background processing (DuckDB convert + schema + preview cache) with WebSocket progress. Use `/settings/set/data_path_simple` to only update the path without processing.
- All persistent DuckDB connections use `memory_limit=500MB` with a per‑user temp directory for spill. This reduces peak memory pressure when ingesting large files.
- Rebuild logic uses the `datasets` catalog in SQLite (`~/.inquira/inquira.db`) and also verifies the expected table exists in DuckDB, so manual table deletions are detected and fixed on the next run.
---

## Admin / Utilities

CLI helpers at `src/inquira/utils/db_tools.py`:

- List DuckDB tables (read‑only; falls back to catalog on lock):
  - `python -m inquira.utils.db_tools list <user|username>`
- List catalog tables (SQLite):
  - `python -m inquira.utils.db_tools catalog <user|username>`
- List dataset file paths (SQLite):
  - `python -m inquira.utils.db_tools paths <user|username>`
- Delete a DuckDB table (requires closing app connections first):
  - `python -m inquira.utils.db_tools delete <user|username> <table>`
- Tip: If the DB is locked, call `POST /settings/close-connections` or stop the server, then retry.
