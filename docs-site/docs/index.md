---
slug: /
---

# Welcome to Inquira

Inquira CE is a privacy-first, local AI data analysis desktop application. By running strictly on your local machine, Inquira ensures your sensitive datasets never leave your device while still giving you the power of an AI-assisted data workflow.

## What is Inquira?

In plain terms: you ask a question about your data in natural language, and Inquira's agents will generate Python analysis scripts, autonomously execute them against your data locally, and return the final results, charts, or insights directly to you along with a concise natural language explanation. It bridges the gap between chat-based LLMs and reproducible data science pipelines.

## Coming Soon

*A video demonstration of Inquira's workspace and analysis flow will be placed here soon.*

## Core Features

- **Autonomous AI-Assisted Analysis**: Translates your natural language prompts into Python workflows, independently executes them, and rapidly returns the final answers and charts.
- **Local Python Execution**: Comes with a bundled Jupyter kernel running locally. For robust security, the AI cannot modify your virtual environment arbitrarily; if a new package is needed, it generates the exact `uv` installation command for you to safely run in the integrated terminal.
- **Seamless Local Data Handling**: Inquira natively connects to your Excel, CSV, JSON, and Parquet files. It dynamically converts them into extremely fast, local DuckDB workspaces capable of analyzing data of any size that fits on your machine.
- **Integrated Code Editor**: Want full control? The workspace includes a built-in code editor with autocomplete. You can manually tweak the AI-generated code, execute it, and debug any issues in a dedicated error pane.
- **Interactive Visualization & Exploring**: Explore generated Plotly charts instantly. Data tables are rendered using AG Grid with a streaming backend (handling up to 2000 rows at a time) to ensure a high-performance, low-memory footprint view of massive datasets.
- **Flawless Resume & Persistence**: Never lose your context. Intermediate variables, artifacts, and local results are saved continuously. You can close the app and resume exactly where you left off later without having to reconnect datasets or rerun expensive computations.
- **Real-Time Visibility & Built-in Terminal**: Watch the agent's thought process through real-time chat token streaming, and leverage the built-in workspace terminal for manual execution and debugging.

## Who is this for?

**Primary Users**
- **Data Scientists and Data Analysts** who know Python. It supercharges your existing workflow by handling the boilerplate code generation while offering complete privacy and local control over the environment.

**Secondary Users**
- **Professionals with many Excel/CSV files** who need to find patterns or analyze data quickly. Inquira speeds up your daily processes so you don't have to depend on an analyst for every descriptive question about your data.
  - *Note:* We strongly recommend users keep an eye on the results to ensure the AI isn't hallucinating numbers. (We will be adding a dedicated section on test results in the future to help increase trust in accuracy).

## Next Steps

If this is your first time here, you can grab the desktop application from the <a href="/download" style={{ color: '#25c2a0', fontWeight: 'bold', textDecoration: 'underline' }}>Download</a> link in the top navigation bar.

If you are evaluating product sign-in and account architecture, read about our [Authentication Strategy](./auth-strategy.md) and [Editions](./editions.md).
