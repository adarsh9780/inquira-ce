# Prompts Directory

This directory contains Jinja2 templates for LLM prompts used throughout the Inquira application.

## How to Add a New Prompt

1. **Create a new `.jinja` file** in this directory
2. **Use Jinja2 template syntax** for variables: `{{ variable_name }}`
3. **The filename becomes the prompt name** (without `.jinja` extension)

## Example

**File:** `my_new_prompt.jinja`

```jinja
You are a {{ role }}. Please help with {{ task }}.

Context: {{ context }}
```

**Usage in code:**

```python
from src.inquira.prompt_library import get_prompt

prompt = get_prompt("my_new_prompt",
                   role="data analyst",
                   task="data visualization",
                   context="sales data")
```

## Available Prompts

### `business_analysis_system`

**Purpose**: System-level instructions for business analysis conversations
**Key Features**:

- Defines role as Business Analyst and Data Scientist
- Establishes DuckDB as primary data processing engine
- Provides structured 4-step analysis framework (Understanding → Strategy → Implementation → Insights)
- Enforces code generation rules and security checks
- Returns structured JSON with `is_safe`, `is_relevant`, `code`, and `explanation`

### `business_analysis_user`

**Purpose**: Formats user questions for optimal LLM processing
**Key Features**:

- Adds business analysis context to user queries
- Identifies relevant metrics and KPIs
- Suggests analytical approaches
- Ensures JSON response structure
- Includes technical instructions for code generation

### `schema_generation`

**Purpose**: Generates detailed column descriptions from data samples
**Key Features**:

- Analyzes data structure and sample values
- Incorporates business domain context
- Creates comprehensive schema descriptions
- Supports multiple data types and formats
- Generates human-readable column explanations

### `code_review`

**Purpose**: Provides code quality assessment and improvement suggestions
**Key Features**:

- Evaluates code structure and readability
- Identifies security vulnerabilities
- Suggests performance optimizations
- Recommends best practices
- Supports multiple programming languages

### `sql_optimizer`

**Purpose**: Analyzes and optimizes SQL queries for better performance
**Key Features**:

- Identifies performance bottlenecks
- Suggests index improvements
- Recommends query restructuring
- Provides execution plan analysis
- Supports multiple database types

## Business Analysis Framework

The business analysis prompts follow a structured 4-step framework:

### 1. Business Understanding

- Analyze the business context and objectives
- Identify key metrics and KPIs
- Formulate hypotheses to test

### 2. Data Analysis Strategy

- Determine required data and analytical methods
- Plan the analysis workflow
- Choose appropriate tools (DuckDB vs Pandas)

### 3. Technical Implementation

- Generate efficient Python code using DuckDB
- Apply statistical and analytical functions
- Create visualizations with Plotly

### 4. Insights & Recommendations

- Interpret results in business context
- Provide actionable recommendations
- Suggest next steps for deeper analysis

## Code Generation Rules

### DuckDB Preference

- **Primary Engine**: Use DuckDB for ALL data querying, filtering, and aggregation
- **Performance**: DuckDB provides 5-10x faster queries than Pandas for large datasets
- **Syntax**: Use `conn.sql("SELECT ...")` for all database operations
- **Connection**: Always available as `conn` variable in execution environment

### Pandas Usage (Secondary)

- Use only when DuckDB cannot handle complex transformations
- Apply for pivot tables and cross-tabulations
- Use for advanced statistical analysis requiring Pandas-specific functions

### Variable Naming

- Use clear, descriptive, and unique names for both DataFrames and Plotly figures so results don’t overwrite each other.
- Examples:
  - DataFrames: `sales_by_region_df`, `monthly_trend_df`
  - Figures: `sales_by_region_fig`, `monthly_trend_chart`
- Reserved/injected: `conn` (DuckDB connection)

### Response Structure

All prompts return structured JSON:

```json
{
  "is_safe": true,
  "is_relevant": true,
  "code": "Python code here",
  "explanation": "Business-focused explanation"
}
```

## Benefits

- **Auto-discovery**: New prompts are automatically available
- **Version control**: Each prompt has its own git history
- **Template power**: Full Jinja2 templating capabilities
- **Organization**: One prompt per file for better maintainability
- **Industry standard**: Follows common practices for template management
