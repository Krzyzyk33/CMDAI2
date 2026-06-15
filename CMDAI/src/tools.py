import os
import re
import glob as pyglob
import subprocess
import shutil
from typing import List, Dict, Any, Optional
def read_file(path: str, offset: int = 0, limit: Optional[int] = None) -> str:
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        end = offset + limit if limit else len(lines)
        subset = lines[offset:end]
        return "".join([f"{i+offset+1}| {line}" for i, line in enumerate(subset)])
def create_file(path: str, content: str) -> str:
    if os.path.exists(path):
        return f"Error: File {path} already exists."
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Success: File {path} created."
def edit_file(path: str, old_str: str, new_str: str) -> str:
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    count = content.count(old_str)
    if count == 0:
        return "Error: old_str not found in file."
    elif count > 1:
        return "Error: old_str is ambiguous, found multiple times. Provide more context."
        
    new_content = content.replace(old_str, new_str)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return f"Success: Replaced old_str with new_str in {path}."
def write_file(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Success: File {path} overwritten."
def delete_file(path: str) -> str:
    if not os.path.exists(path):
        return f"Error: Path {path} not found."
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    return f"Success: {path} deleted."
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
def run_grep(pattern: str, path: str = ".", glob_pattern: Optional[str] = None) -> str:
    # Basic implementation of grep in python
    results = []
    if os.path.isfile(path):
        files = [path]
    else:
        files = []
        for root, _, filenames in os.walk(path):
            for f in filenames:
                if glob_pattern:
                    import fnmatch
                    if not fnmatch.fnmatch(f, glob_pattern):
                        continue
                files.append(os.path.join(root, f))
                
    try:
        regex = re.compile(pattern)
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if regex.search(line):
                            results.append(f"{filepath}:{i+1}:{line.strip()}")
            except (UnicodeDecodeError, PermissionError):
                continue
    except Exception as e:
        return f"Error: {str(e)}"
        
    if not results:
        return "No matches found."
    return "\n".join(results[:500]) # Limit output
def run_glob(pattern: str) -> str:
    matches = pyglob.glob(pattern, recursive=True)
    if not matches:
        return "No files found matching pattern."
    return "\n".join(matches)
def run_ls(path: str = ".") -> str:
    if not os.path.exists(path):
        return f"Error: Path {path} not found."
    if os.path.isfile(path):
        return path
    entries = os.listdir(path)
    if not entries:
        return "Empty directory."
    return "\n".join(entries)
def todo_write(items: List[str]) -> str:
    # Actual UI update handled in agent/ui loop
    return "Todo list updated."
def search_web(query: str) -> str:
    if query.startswith("http://") or query.startswith("https://"):
        try:
            import urllib.request
            import re
            req = urllib.request.Request(query, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                # Proste usuwanie tagów script, style i HTML
                html = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', html)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:4000]
        except Exception as e:
            return f"Error reading URL: {e}"

    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            
        if not results:
            return f"No results found for \"{query}\"."
            
        out = f"Results for \"{query}\":\n\n"
        for i, res in enumerate(results):
            title = res.get('title', 'No title')
            href = res.get('href', '')
            body = res.get('body', 'No snippet available')
            out += f"{i+1}. {title}\n   Link: {href}\n   Snippet: {body}\n\n"
        return out
    except Exception as e:
        return f"Error executing web search: {str(e)}"
def save_plan(content: str, restricted_dir: str = None) -> str:
    try:
        path = "plan.md"
        if restricted_dir:
            path = os.path.join(restricted_dir, "plan.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "Plan successfully saved to plan.md"
    except Exception as e:
        return f"Error: {e}"
def mark_plan_step_done(step_number: int, restricted_dir: str = None) -> str:
    try:
        path = "plan.md"
        if restricted_dir:
            path = os.path.join(restricted_dir, "plan.md")
        if not os.path.exists(path):
            return "Error: plan.md does not exist."
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        import re
        lines = content.split('\n')
        step_str = str(step_number)
        
        found = False
        for i, line in enumerate(lines):
            # Prosty regex szukający [ ] przy podanym numerze kroku
            if re.search(r'(?:^|\s)' + step_str + r'\..*?\[ \]', line):
                lines[i] = line.replace('[ ]', '[x]', 1)
                found = True
                break
                
        if found:
            with open(path, "w", encoding="utf-8") as f:
                f.write('\n'.join(lines))
            return f"Step {step_number} marked as done in plan.md"
        else:
            return f"Could not find uncompleted step {step_number} with '[ ]' in plan.md"
    except Exception as e:
        return f"Error: {e}"
def submit_plan(**kwargs) -> str:
    architecture_details = kwargs.get("architecture_details", "No architecture details provided.")
    steps_list = kwargs.get("steps_list")
    
    if not steps_list:
        return "Error: You MUST provide 'steps_list' argument as an array of strings (e.g. ['Step 1', 'Step 2'])."
        
    if isinstance(steps_list, str):
        # Model wrongly passed a single string, try to split by newlines
        steps_list = [s.strip() for s in steps_list.split('\n') if s.strip()]
        
    content = f"# Architecture Details\n{architecture_details}\n\n## Steps\n"
    for i, step in enumerate(steps_list):
        content += f"{i+1}. [ ] {step}\n"
    return save_plan(content)
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

def execute_tool(name: str, args: Dict[str, Any], restricted_dir: Optional[str] = None) -> str:
    if restricted_dir and "path" in args:
        target_path = os.path.abspath(args["path"])
        safe_dir = os.path.abspath(restricted_dir)
        if not target_path.startswith(safe_dir):
            return f"Error: IDE isolation is active. Odmowa dostępu do ścieżki {args['path']} - wykracza poza aktualny projekt."
            
    tools_map = {
        "bash": run_bash,
        "read_file": read_file,
        "create_file": create_file,
        "edit_file": edit_file,
        "write_file": write_file,
        "delete_file": delete_file,
        "run_python": run_python,
        "grep": run_grep,
        "glob": run_glob,
        "ls": run_ls,
        "todo_write": todo_write,
        "search_web": search_web,
        "save_plan": save_plan,
        "mark_plan_step_done": mark_plan_step_done,
        "submit_plan": submit_plan
    }
    
    if name not in tools_map:
        return f"Error: Unknown tool {name}"
        
    try:
        return tools_map[name](**args)
    except TypeError as e:
        return f"Error executing {name}: Invalid arguments. {str(e)}"
    except Exception as e:
        return f"Error executing {name}: {str(e)}"
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Executes a bash or powershell command on the user's system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line string to execute."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads contents of a file, with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "description": "Starting line index (0-based)"},
                    "limit": {"type": "integer", "description": "Number of lines to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Creates a new file. Directories are created automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replaces old_str with new_str in a file. The old_str must be unique.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_str": {"type": "string"},
                    "new_str": {"type": "string"}
                },
                "required": ["path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrites an entire file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Deletes a file or directory recursively.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Runs a python script. Provide either a local 'path' or raw python 'code' to execute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the python file to run"},
                    "code": {"type": "string", "description": "Raw python code to execute immediately"},
                    "timeout": {"type": "integer"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for a regex pattern in files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob_pattern": {"type": "string"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "List files matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ls",
            "description": "List contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": "Writes a list of tasks to the UI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the web using DuckDuckGo OR reads content from a direct URL. If query starts with http:// or https://, it acts as a web scraper and returns the text content of that website. Otherwise, it returns search results links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search phrase OR a direct URL (http/https) to read its content"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_plan",
            "description": "Saves your execution plan to plan.md. ONLY available in plan mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The full markdown content of the plan"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_plan_step_done",
            "description": "Marks a step as done in the plan.md file by replacing [ ] with [x].",
            "parameters": {
                "type": "object",
                "properties": {
                    "step_number": {"type": "integer", "description": "The number of the step to mark as completed (e.g., 1)."}
                },
                "required": ["step_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_plan",
            "description": "Submit an architectural plan before executing changes. Required on Extreme level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "architecture_details": {"type": "string", "description": "Detailed analysis and architectural decisions."},
                    "steps_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of strings describing the execution steps."
                    }
                },
                "required": ["architecture_details", "steps_list"]
            }
        }
    }
]
