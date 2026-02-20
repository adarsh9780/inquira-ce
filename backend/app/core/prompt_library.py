"""
Prompt Library for Inquira

Jinja2-based prompt system with automatic template discovery.
This module provides easy maintenance, updates, and reuse of prompts.
Add new prompts by simply adding .jinja files to the prompts/ directory.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class PromptLibrary:
    """Library for managing all LLM prompts using Jinja2 templates"""

    _jinja_env: Optional[Environment] = None
    _available_prompts: Optional[List[str]] = None

    @classmethod
    def _get_jinja_env(cls) -> Environment:
        """Get or create Jinja2 environment"""
        if cls._jinja_env is not None:
            return cls._jinja_env

        # Get the prompts directory
        current_dir = Path(__file__).parent
        prompts_dir = current_dir / "prompts" / "templates"

        if not prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

        # Create Jinja2 environment
        cls._jinja_env = Environment(
            loader=FileSystemLoader(prompts_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False  # We don't want HTML escaping for prompts
        )

        return cls._jinja_env

    @classmethod
    def _discover_prompts(cls) -> List[str]:
        """Discover all available prompt templates"""
        if cls._available_prompts is not None:
            return cls._available_prompts

        current_dir = Path(__file__).parent
        prompts_dir = current_dir / "prompts" / "templates"

        if not prompts_dir.exists():
            return []

        cls._available_prompts = []
        for file_path in prompts_dir.glob("*.jinja"):
            if file_path.is_file():
                # Remove .jinja extension to get prompt name
                prompt_name = file_path.stem
                cls._available_prompts.append(prompt_name)

        return cls._available_prompts

    @classmethod
    def get_prompt(cls, prompt_name: str, **variables) -> str:
        """Get a prompt by name and render with variables"""
        env = cls._get_jinja_env()
        available_prompts = cls._discover_prompts()

        if prompt_name not in available_prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found. Available prompts: {available_prompts}")

        try:
            template = env.get_template(f"{prompt_name}.jinja")
            return template.render(**variables)
        except TemplateNotFound:
            raise ValueError(f"Template file for '{prompt_name}' not found")
        except Exception as e:
            raise ValueError(f"Error rendering prompt '{prompt_name}': {e}")

    @classmethod
    def get_available_prompts(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all available prompts"""
        available_prompts = cls._discover_prompts()
        env = cls._get_jinja_env()

        result = {}
        for prompt_name in available_prompts:
            try:
                template = env.get_template(f"{prompt_name}.jinja")
                # Try to extract variables from template (basic approach)
                template_source = template.generate()
                # This is a simple heuristic - in practice you might want more sophisticated variable detection
                variables = cls._extract_variables_from_template(template_source)
                result[prompt_name] = {
                    "description": f"Jinja template with variables: {variables}",
                    "variables": variables,
                    "file": f"{prompt_name}.jinja"
                }
            except Exception:
                result[prompt_name] = {
                    "description": "Template file (variables unknown)",
                    "variables": [],
                    "file": f"{prompt_name}.jinja"
                }

        return result

    @classmethod
    def _extract_variables_from_template(cls, template_source) -> List[str]:
        """Extract variable names from Jinja template"""
        variables = []
        import re

        # Find all {{ variable }} patterns, including those with filters
        # Matches: {{ var }}, {{ var | filter }}, {{ var.attr }}, etc.
        matches = re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*(?:\s*\|\s*[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}', template_source)

        # Clean up variable names (remove filters and attributes)
        for match in matches:
            # Take only the base variable name (before any . or |)
            var_name = match.split('.')[0].split('|')[0].strip()
            if var_name and var_name not in variables:
                variables.append(var_name)

        return variables

    @classmethod
    def reload_prompts(cls):
        """Force reload templates and rediscover prompts (useful for development)"""
        cls._jinja_env = None
        cls._available_prompts = None
        # Force rediscovery
        cls._discover_prompts()


# Convenience functions for backward compatibility and easy access
def get_prompt(prompt_name: str, **variables) -> str:
    """Get any prompt by name with variables"""
    return PromptLibrary.get_prompt(prompt_name, **variables)

def get_business_analysis_system_instruction(**kwargs) -> str:
    """Convenience function to get business analysis system instruction"""
    return PromptLibrary.get_prompt("business_analysis_system", **kwargs)

def get_business_analysis_user_question(**kwargs) -> str:
    """Convenience function to get business analysis user question"""
    return PromptLibrary.get_prompt("business_analysis_user", **kwargs)

def get_schema_generation_prompt(**kwargs) -> str:
    """Convenience function to get schema generation prompt"""
    return PromptLibrary.get_prompt("schema_generation", **kwargs)

def get_available_prompts() -> Dict[str, Dict[str, Any]]:
    """Get information about all available prompts"""
    return PromptLibrary.get_available_prompts()