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

def run_ls(path: str = ".") -> str:
    if not os.path.exists(path):
        return f"Error: Path {path} not found."
    if os.path.isfile(path):
        return path
    entries = os.listdir(path)
    if not entries:
        return "Empty directory."
    return "\n".join(entries)

def run_glob(pattern: str) -> str:
    matches = pyglob.glob(pattern, recursive=True)
    if not matches:
        return "No files found matching pattern."
    return "\n".join(matches)

