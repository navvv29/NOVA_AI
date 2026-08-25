import io
import traceback
import threading
from contextlib import redirect_stdout, redirect_stderr

from langchain_core.tools import tool


@tool
def run_code(code: str, timeout: int = 10) -> str:
    """Execute Python code in a safe sandbox and return the output.

    Use this for:
    - Learning: Run code examples to see how they work
    - Testing: Verify code before using it
    - Calculations: Quick math or data processing
    - Prototyping: Test ideas quickly

    Parameters:
    - code: Python code to execute
    - timeout: Maximum execution time in seconds (default 10, max 30)

    The code runs with restricted access:
    - No file system access (use read_file/write_file tools instead)
    - No network access
    - Limited execution time
    - stdout and stderr are captured
    """
    timeout = min(max(1, timeout), 30)
    result = {"output": "", "error": "", "killed": False}

    # Safety check: block dangerous operations
    dangerous = ["os.system", "subprocess", "shutil.rmtree", "open(", "import os", "import subprocess"]
    code_lower = code.lower()
    for pattern in dangerous:
        if pattern.lower() in code_lower:
            return (
                f"⚠️ Blocked: Code contains restricted operation '{pattern}'.\n"
                f"For file operations, use the read_file/write_file tools instead.\n"
                f"For system commands, describe what you need and I'll help."
            )

    # Capture output
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        # Create a restricted namespace
        namespace = {
            "__builtins__": {
                "print": print,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "bool": bool,
                "type": type,
                "isinstance": isinstance,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "reversed": reversed,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "pow": pow,
                "divmod": divmod,
                "True": True,
                "False": False,
                "None": None,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "Exception": Exception,
            }
        }

        def _run():
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(compile(code, "<sandbox>", "exec"), namespace)
            except Exception:
                result["error"] = traceback.format_exc()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            result["killed"] = True

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        result_parts = []
        if result["killed"]:
            result_parts.append(f"Timeout: code was stopped after {timeout}s.")
        if stdout_output:
            result_parts.append(f"Output:\n{stdout_output}")
        if stderr_output:
            result_parts.append(f"Errors/Warnings:\n{stderr_output}")
        if result["error"] and not result["killed"]:
            result_parts.append(f"Execution Error:\n{result['error']}")
        if not stdout_output and not stderr_output and not result["error"] and not result["killed"]:
            result_parts.append("Code executed successfully (no output).")

        return "\n".join(result_parts)

    except Exception as e:
        error_trace = traceback.format_exc()
        return f"Execution Error:\n{error_trace}"
