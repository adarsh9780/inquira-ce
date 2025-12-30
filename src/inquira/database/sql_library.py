"""
SQL Template Library for Inquira

Centralized Jinja2-based SQL templates with safe quoting helpers.
"""

from pathlib import Path
from typing import Optional
import re
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class SqlLibrary:
    _jinja_env: Optional[Environment] = None

    @classmethod
    def _get_env(cls) -> Environment:
        if cls._jinja_env is not None:
            return cls._jinja_env

        base_dir = Path(__file__).parent
        templates_dir = base_dir / "sql"

        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )

        # Filters
        def sql_quote(value) -> str:
            if value is None:
                return ''
            s = str(value)
            return s.replace("'", "''")

        ident_safe_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

        def sql_ident(name) -> str:
            if name is None:
                return '""'
            s = str(name)
            if ident_safe_re.match(s):
                return s
            s = s.replace('"', '""')
            return f'"{s}"'

        env.filters['sql_quote'] = sql_quote
        env.filters['sql_ident'] = sql_ident

        cls._jinja_env = env
        return env

    @classmethod
    def get_sql(cls, template_name: str, **variables) -> str:
        env = cls._get_env()
        try:
            tmpl = env.get_template(f"{template_name}.sql.j2")
            return tmpl.render(**variables)
        except TemplateNotFound as e:
            raise ValueError(f"SQL template not found: {template_name}") from e


def get_sql(template_name: str, **variables) -> str:
    return SqlLibrary.get_sql(template_name, **variables)

