from typing import Any, Dict, Optional, Tuple

from .config_models import AppConfig

class CodeExecutionError(Exception):
    """Raised when code execution fails"""
    pass

class TimeoutError(Exception):
    """Raised when code execution times out"""
    pass

class CodeWhisperer:
    """Python code execution"""

    def __init__(self, config: AppConfig):
        self.config = config
        self._local_vars: Dict[str, Any] = {}
        self._global_vars = {
            '__builtins__': __builtins__
        }


    def execute_code(self, code: str) -> Tuple[Any, Optional[str]]:
        """
        Execute Python code

        Returns:
            Tuple of (result: Any, error_message: Optional[str])
        """
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
        Execute Python code and return all pandas DataFrames, plotly figures, and scalar variables

        Scans all variables created by the code and categorizes them into:
        - dataframes: Dictionary of all pandas DataFrames converted to JSON {"var_name": "json_data"}
        - figures: Dictionary of all plotly figures converted to JSON {"var_name": "json_data"}
        - scalars: Dictionary of all JSON serializable scalar values {"var_name": value}

        Returns:
            Tuple of (result: Any, variables: Dict[str, Any], error_message: Optional[str])
        """
        try:
            # Create fresh local and global environments for this execution
            exec_globals = self._global_vars.copy()
            exec_locals = self._local_vars.copy()

            # Execute the code
            exec(code, exec_globals, exec_locals)

            # Initialize result dictionaries
            dataframes = {}
            figures = {}
            scalars = {}

            # Helper function to check if value is JSON serializable
            def is_json_serializable(value):
                try:
                    import json
                    json.dumps(value)
                    return True
                except (TypeError, ValueError):
                    return False

            # Scan all variables in both locals and globals
            all_vars = {}
            all_vars.update(exec_globals)
            all_vars.update(exec_locals)  # locals take precedence

            for var_name, var_value in all_vars.items():
                if var_name == '__builtins__' or var_value is None:
                    continue

                try:
                    # Check for pandas DataFrames
                    if hasattr(var_value, '__class__'):
                        type_str = str(type(var_value))
                        if 'DataFrame' in type_str and 'pandas' in type_str:
                            if hasattr(var_value, 'to_json'):
                                try:
                                    dataframes[var_name] = var_value.to_json(orient="records")
                                except Exception:
                                    dataframes[var_name] = None
                            continue

                        # Check for plotly figures
                        type_str_lower = type_str.lower()
                        if 'plotly' in type_str_lower and 'figure' in type_str_lower:
                            if hasattr(var_value, 'to_json'):
                                try:
                                    figures[var_name] = var_value.to_json()
                                except Exception:
                                    figures[var_name] = None
                            continue

                    # Check for scalar values (JSON serializable)
                    if is_json_serializable(var_value):
                        scalars[var_name] = var_value
                    else:
                        # Convert to string for non-serializable values
                        scalars[var_name] = str(var_value)

                except Exception:
                    # If there's any error processing a variable, skip it
                    continue

            # Structure the variables response
            variables = {
                'dataframes': dataframes,
                'figures': figures,
                'scalars': scalars
            }

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