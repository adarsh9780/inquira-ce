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

- `business_analysis_system` - System prompt for business analysis
- `business_analysis_user` - User question template for business analysis
- `schema_generation` - Schema description generation
- `code_review` - Code review and feedback
- `sql_optimizer` - SQL query optimization

## Benefits

- **Auto-discovery**: New prompts are automatically available
- **Version control**: Each prompt has its own git history
- **Template power**: Full Jinja2 templating capabilities
- **Organization**: One prompt per file for better maintainability
- **Industry standard**: Follows common practices for template management
