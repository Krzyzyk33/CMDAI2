import os
import re
import glob as pyglob
import subprocess
import shutil
from typing import List, Dict, Any, Optional

def run_python(path: str = "", code: str = "", timeout: int = 30) -> str:
    if not path and not code:
        return "Error: Provide either 'path' or 'code'."
        
    import subprocess
    import os
    if code:
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".py", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
        script_to_run = temp_path
    else:
        if not os.path.exists(path):
            return f"Error: File {path} not found."
        script_to_run = path

    try:
        result = subprocess.run(
            ["python", script_to_run],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = f"Exit code: {result.returncode}\n"
        if result.stdout:
            out += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            out += f"STDERR:\n{result.stderr}\n"
        return out
    except subprocess.TimeoutExpired:
        return f"Error: Script timed out after {timeout} seconds."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if code and os.path.exists(script_to_run):
            try:
                os.remove(script_to_run)
            except:
                pass

def run_bash(command: str, timeout: int = 30) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        out = f"Exit code: {result.returncode}\n"
        if result.stdout:
            out += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            out += f"STDERR:\n{result.stderr}\n"
        return out
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing bash: {str(e)}"

