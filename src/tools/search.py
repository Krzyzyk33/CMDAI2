import os
import re
import glob as pyglob
import subprocess
import shutil
from typing import List, Dict, Any, Optional

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
    return "\n".join(results[:500])

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

