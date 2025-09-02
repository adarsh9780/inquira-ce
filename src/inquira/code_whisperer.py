import ast
import sys
import subprocess
import tempfile
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from .config_models import AppConfig

class CodeSecurityError(Exception):
    """Raised when code contains security violations"""
    pass

class CodeExecutionError(Exception):
    """Raised when code execution fails"""
    pass

class TimeoutError(Exception):
    """Raised when code execution times out"""
    pass

class CodeWhisperer:
    """Safe Python code execution with AST analysis"""

    def __init__(self, config: AppConfig):
        self.config = config
        self._local_vars = {}
        self._global_vars = {
            '__builtins__': {
                '__import__': __import__,
                'print': print,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'all': all,
                'any': any,
                'bool': bool,
                'int': int,
                'float': float,
                'str': str,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'dir': dir,
                'vars': vars,
                'id': id,
                'hash': hash,
                'repr': repr,
                'format': format,
            }
        }

    def analyze_code(self, code: str) -> Tuple[bool, List[str]]:
        """
        Analyze Python code using AST to check for security violations

        Returns:
            Tuple of (is_safe: bool, violations: List[str])
        """
        try:
            tree = ast.parse(code)
            violations = []

            # Walk through the AST and check for violations
            for node in ast.walk(tree):
                violations.extend(self._check_node(node))

            is_safe = len(violations) == 0
            return is_safe, violations

        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]
        except Exception as e:
            return False, [f"AST parsing error: {e}"]

    def _check_node(self, node: ast.AST) -> List[str]:
        """Check individual AST nodes for security violations"""
        violations = []

        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not self.config.is_library_allowed(alias.name):
                    violations.append(f"Import not allowed: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module and not self.config.is_library_allowed(node.module):
                violations.append(f"Import not allowed: {node.module}")

        # Check function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if not self.config.is_function_allowed(func_name):
                    violations.append(f"Function call not allowed: {func_name}")

        # Check attribute access (potential security risk)
        elif isinstance(node, ast.Attribute):
            # Check for dangerous attribute access
            if isinstance(node.value, ast.Name):
                if node.value.id in ['os', 'sys', 'subprocess', 'multiprocessing']:
                    violations.append(f"Dangerous attribute access: {node.value.id}.{node.attr}")

        # Check for file operations if not allowed
        if not self.config.ALLOW_FILE_OPERATIONS:
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ['open', 'file']:
                    violations.append("File operations not allowed")

        # Check for network operations if not allowed
        if not self.config.ALLOW_NETWORK_OPERATIONS:
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ['socket', 'http', 'urllib', 'requests']:
                            violations.append("Network operations not allowed")

        # Check for system operations if not allowed
        if not self.config.ALLOW_SYSTEM_OPERATIONS:
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ['os', 'sys', 'subprocess']:
                            violations.append("System operations not allowed")

        return violations

    def execute_code(self, code: str) -> Tuple[Any, Optional[str]]:
        """
        Execute Python code safely with security analysis

        Returns:
            Tuple of (result: Any, error_message: Optional[str])
        """
        # First analyze the code for security
        is_safe, violations = self.analyze_code(code)
        if not is_safe:
            raise CodeSecurityError(f"Code contains security violations: {'; '.join(violations)}")

        try:
            # Execute the code using exec with restricted environment
            exec(code, self._global_vars, self._local_vars)

            # Try to get the last expression result if it's an expression
            try:
                # If the code is a simple expression, evaluate it to get the result
                result = eval(code, self._global_vars, self._local_vars)
                return result, None
            except:
                # If it's not a simple expression, return success message
                return "Code executed successfully", None

        except Exception as e:
            return None, f"Execution error: {str(e)}"

    def execute_with_timeout(self, code: str, timeout: Optional[int] = None) -> Tuple[Any, Optional[str]]:
        """Execute code with a custom timeout"""
        # For now, execute directly without threading to avoid resource limit issues
        # TODO: Implement proper timeout mechanism
        try:
            return self.execute_code(code)
        except Exception as e:
            return None, str(e)

    def execute_with_variables(self, code: str) -> Tuple[Any, Dict[str, Any], Optional[str]]:
        """
        Execute Python code and return created variables

        Returns:
            Tuple of (result: Any, variables: Dict[str, Any], error_message: Optional[str])
        """
        # First analyze the code for security
        is_safe, violations = self.analyze_code(code)
        if not is_safe:
            raise CodeSecurityError(f"Code contains security violations: {'; '.join(violations)}")

        try:
            # Create fresh local and global environments for this execution
            exec_globals = self._global_vars.copy()
            exec_locals = self._local_vars.copy()

            # Track variables before execution
            initial_vars = set(exec_locals.keys()) | set(exec_globals.keys())
            initial_vars.add('__builtins__')  # Exclude builtins

            # Execute the code
            exec(code, exec_globals, exec_locals)

            # Only return specific variables: result_df and figure
            variables = {}

            # Handle result_df variable
            result_df_value = None
            if 'result_df' in exec_locals:
                result_df_value = exec_locals['result_df']
            elif 'result_df' in exec_globals:
                result_df_value = exec_globals['result_df']

            if result_df_value is not None:
                # Check if it's a pandas DataFrame and convert to JSON
                if hasattr(result_df_value, 'to_json') and hasattr(result_df_value, '__class__'):
                    try:
                        if 'DataFrame' in str(type(result_df_value)):
                            variables['result_df'] = result_df_value.to_json(orient="records")
                        else:
                            variables['result_df'] = None
                    except:
                        variables['result_df'] = None
                else:
                    variables['result_df'] = None
            else:
                variables['result_df'] = None

            # Handle figure variable
            figure_value = None
            if 'figure' in exec_locals:
                figure_value = exec_locals['figure']
            elif 'figure' in exec_globals:
                figure_value = exec_globals['figure']

            if figure_value is not None:
                # Check if it's a plotly figure and convert to JSON
                if hasattr(figure_value, 'to_json') and hasattr(figure_value, 'data'):
                    try:
                        if 'plotly' in str(type(figure_value)).lower():
                            variables['figure'] = figure_value.to_json()
                        else:
                            variables['figure'] = None
                    except:
                        variables['figure'] = None
                else:
                    variables['figure'] = None
            else:
                variables['figure'] = None

            # Try to get the last expression result if it's an expression
            try:
                result = eval(code, exec_globals, exec_locals)

                # Handle result serialization
                if result is not None:
                    # Handle pandas DataFrame result
                    if hasattr(result, 'to_json') and hasattr(result, '__class__'):
                        try:
                            if 'DataFrame' in str(type(result)):
                                result = result.to_json(orient="records")
                        except:
                            pass

                    # Handle DuckDB connection result
                    if hasattr(result, '__class__'):
                        try:
                            type_str = str(type(result))
                            if 'duckdb' in type_str.lower() and 'connection' in type_str.lower():
                                result = f"DuckDB Connection: {str(result)}"
                        except:
                            pass

                    # Handle plotly figure result
                    if hasattr(result, 'to_json') and hasattr(result, 'data'):
                        try:
                            if 'plotly' in str(type(result)).lower():
                                result = result.to_json()
                        except:
                            pass

                    # Handle matplotlib figure result
                    if hasattr(result, 'savefig'):
                        try:
                            import io
                            import base64
                            buf = io.BytesIO()
                            result.savefig(buf, format='png')
                            buf.seek(0)
                            result = f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"
                        except:
                            pass

                    # Check if the result is JSON serializable
                    try:
                        import json
                        json.dumps(result)
                    except (TypeError, ValueError):
                        # If not serializable, convert to string representation
                        result = str(result)

            except:
                result = "Code executed successfully"

            return result, variables, None

        except Exception as e:
            return None, {}, f"Execution error: {str(e)}"

    def reset_environment(self):
        """Reset the execution environment"""
        self._local_vars.clear()
        # Keep the restricted builtins