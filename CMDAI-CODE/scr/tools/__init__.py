import os
from typing import List, Dict, Any, Optional
from .filesystem import read_file, create_file, edit_file, write_file, delete_file, run_ls, run_glob
from .execution import run_python, run_bash
from .search import run_grep, search_web
from .planning import save_plan, mark_plan_step_done, submit_plan, todo_write

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
