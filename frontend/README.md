# 🚀 Inquira - AI-Powered Data Analysis Tool

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue.js-3-4FC08D?style=for-the-badge&logo=vue.js" alt="Vue.js">
  <img src="https://img.shields.io/badge/FastAPI-00C853?style=for-the-badge&logo=fastapi" alt="FastAPI">
</p>

<p align="center">
  <strong>Transform natural language into powerful data insights with AI-generated Python code</strong>
</p>

<p align="center">
  <img src="./assets/demo-screenshot.png" alt="Inquira Demo" width="800">
</p>

---

## 📋 Table of Contents

- [🎯 What is Inquira?](#-what-is-inquira)
- [🆕 What's New](#-whats-new)
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
- **Python** 3.10+
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
# - Excel files (.xlsx, .xls)
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

The sidebar is vertical on the left. When collapsed, tabs show a small count badge (e.g., number of tables/figures, ✓ for ready code) and a brief green pulse when new output arrives.

### 🧭 Preview & Schema
- Preview tab provides a quick, readable data preview (sticky header, hover column descriptions)
- Schema tab lets you edit/save schema and export it as JSON

### 🧠 Default Code Template
The default analysis uses your backend-declared table name from `/settings/view` and provides:
- A quick sample (LIMIT 100)
- Schema via `DESCRIBE SELECT`
- Row count
- A pandas `describe()` summary on a capped sample (LIMIT 5000)

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
│ • CodeMirror    │    │ • Data Processing│    │ • Code Generation│
│ • AG Grid/Table │    │ • File Upload    │    │ • Query Optimization│
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
- **Code Editor**: CodeMirror 6
- **Data Grid**: AG Grid (Table tab); simple sticky table for Preview tab
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
POST   /export/chart    # Export chart as image
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
- **⚡ Local Python Execution**: Runs locally with your operating-system user permissions
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

#### **4. Memory Issues**
```bash
# For large datasets, increase memory
export PYTHONPATH=/usr/local/lib/python3.10
# Or use chunked processing
```

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
uv run python src/backend/main.py
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

- Code execution is local and is not sandboxed; it runs with your operating-system user permissions
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

---

## 🆕 What's New

- Vertical tab navigation on the left with collapsed mode and count badges.
- Chat as a toggleable 25% overlay (press `H`) that doesn’t interrupt your current tab.
- Preview and Schema are first‑class tabs (modal removed):
  - Preview uses a clean sticky table with hover column descriptions.
  - Schema Editor supports inline edits, save, export, clear cache.
- Output indicators: small count badges and a brief green pulse when new output arrives (works while collapsed).
- Table and Figure show latest outputs first by default.
- Code editor improvements: `Tab`/`Shift+Tab` indent/outdent (4 spaces).
- Default code template unified: uses backend table name from `/settings/view` and includes sample, schema (DESCRIBE), row count, and pandas `describe()` summary.
- Plotly charts reliably fill available space on first render (responsive + resize observer).
- AG Grid theming migrated to the Theming API (Quartz) and legacy CSS removed in affected views.
