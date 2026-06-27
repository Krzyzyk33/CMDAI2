from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
import time
import sys
console = Console()
# Theme Colors (from Claude Code style)
ACCENT_COLOR = "white"  # White
MUTED_COLOR = "gray50"
SUCCESS_COLOR = "green"
ERROR_COLOR = "red"
def print_header(model_name: str, cwd: str):
    from rich import box
    import json, os
    engine_short = "cpp"
    state_file = os.path.expanduser("~/.cmdai2/state.json")
    try:
        with open(state_file, "r") as f:
            state = json.load(f)
            cwd = state.get("cwd", cwd)
    except:
        pass

    header_text = Text()
    header_text.append(f"✻ CMDAI CODE  ·   {model_name}  ·   {engine_short}\n", style=ACCENT_COLOR)
    header_text.append(f"cwd: {cwd}   /help · /review · @plik · ⇧Tab", style=MUTED_COLOR)
    
    panel = Panel(header_text, border_style=ACCENT_COLOR, padding=(0, 2), box=box.ROUNDED)
    console.print(panel)
def print_user_msg(msg: str):
    console.print(f"\n\n[bold]> {msg}[/bold]")
def print_agent_msg(msg: str):
    console.print(f"[{ACCENT_COLOR}]✻[/] {msg}")
    
def print_tool_call(tool_name: str, arg_summary: str):
    name_lower = tool_name.lower()
    if name_lower in ["read_file", "read"]:
        console.print(f"\n[bold]● Read: {arg_summary}[/bold]")
    elif name_lower in ["edit_file", "edit"]:
        console.print(f"\n[bold]● Edit: {arg_summary}[/bold]")
    elif name_lower in ["write_file", "create_file", "write", "create"]:
        console.print(f"\n[bold]● New file: {arg_summary}[/bold]")
    elif name_lower == "todo_write":
        console.print(f"\n[bold]● Task Plan[/bold]")
    elif name_lower == "bash":
        console.print(f"\n[bold]● Command: {arg_summary}[/bold]")
    elif name_lower == "run_python":
        console.print(f"\n[bold]● Python Script: {arg_summary}[/bold]")
    elif name_lower == "delete_file":
        console.print(f"\n[bold]● Delete: {arg_summary}[/bold]")
    else:
        console.print(f"\n[bold]● Tool ({tool_name}): {arg_summary}[/bold]")
def print_tool_result(result_summary: str):
    console.print(f"[{MUTED_COLOR}]  ⎿  {result_summary}[/]")
from rich.syntax import Syntax
def print_diff(path: str, old_str: str, new_str: str):
    import difflib
    old_lines = old_str.splitlines() if old_str else []
    new_lines = new_str.splitlines() if new_str else []
    diff_lines = list(difflib.unified_diff(old_lines, new_lines, lineterm='', n=3))
    
    # Usuwamy nagłówki unified diff (---, +++)
    if len(diff_lines) > 2:
        diff_lines = diff_lines[2:]
        
    diff_content = "\n".join(diff_lines) if diff_lines else "No changes detected."
    print_code_panel(f"{path} (Diff)", diff_content, lexer_override="diff")
def print_code_panel(path: str, content: str, lexer_override: str = None):
    lexer = lexer_override or "text"
    if not lexer_override:
        if path.endswith(".py"): lexer = "python"
        elif path.endswith(".js") or path.endswith(".ts"): lexer = "javascript"
        elif path.endswith(".html"): lexer = "html"
        elif path.endswith(".css"): lexer = "css"
        elif path.endswith(".go"): lexer = "go"
        elif path.endswith(".json"): lexer = "json"
    
    p = path.replace("\\", "/")
    parts = p.split("/")
    display_title = ".../" + "/".join(parts[-3:]) if len(parts) > 3 else p
    
    lines = content.splitlines()
    display_content = "\n".join(lines[:20])
    subtitle = f"[gray50]... (and {len(lines)-20} more lines)[/gray50]" if len(lines) > 20 else None
        
    syntax = Syntax(display_content, lexer, theme="monokai", line_numbers=True, word_wrap=True)
    panel = Panel(syntax, title=f"[bold]{display_title}[/bold]", title_align="left", subtitle=subtitle, subtitle_align="right", border_style=ACCENT_COLOR)
    console.print(panel)
import rich.spinner
rich.spinner.SPINNERS["claude"] = {"interval": 120, "frames": ["✻", "✽", "✶", "✢"]}
def format_time(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m = s // 60
    sec = s % 60
    return f"{m}m {sec}s"
class ThinkingTree:
    def __init__(self, expanded=True, simulate=False, title="Thinking", model_name=None):
        self.expanded = expanded
        self.simulate = simulate
        self.title = title
        self.model_name = model_name
        self.lines = []
        self.spinner_frames = ["⌬", "✻"]
        self.frame_idx = 0
        self.fake_thoughts = [
            "Analyzing prompt and context...",
            "Verifying available system tools...",
            "Designing solution architecture...",
            "Checking syntax and dependencies...",
            "Optimizing logic...",
            "Preparing code implementation..."
        ]
        self.fake_added = 0
        
        self.start_time = time.time()
        self.live = Live(get_renderable=self.render, refresh_per_second=5, transient=False)
        
    def start(self):
        self.start_time = time.time()
        self.live.start()
        
    def add_line(self, line: str):
        self.simulate = False
        lstripped = line.lstrip()
        spaces = len(line) - len(lstripped)
        
        import re
        # Auto-detect lists and sub-lists for better tree formatting
        if re.match(r'^(-\s|\*\s|\d+\.\s|[a-zA-Z]\.\s)', lstripped) and spaces < 2:
            spaces = 2
        elif re.match(r'^\d+\.\d+\.\s', lstripped) and spaces < 4:
            spaces = 4
            
        if re.match(r'^(-\s|\*\s)', lstripped):
            content = lstripped[2:].strip()
        else:
            content = lstripped.strip()
            
        self.lines.append(" " * spaces + content)
            
    def render(self):
        self.frame_idx = (self.frame_idx + 1) % len(self.spinner_frames)
        sym = self.spinner_frames[self.frame_idx]
        elapsed_sec = time.time() - self.start_time
        
        if self.simulate and self.fake_added < len(self.fake_thoughts):
            if int(elapsed_sec) > (self.fake_added + 1) * 12:
                self.lines.append(self.fake_thoughts[self.fake_added])
                self.fake_added += 1
        
        t = Text()
        model_str = f" · {self.model_name}" if self.model_name else ""
        t.append(f"\n{sym} {self.title}... ({format_time(elapsed_sec)}{model_str})\n", style=ACCENT_COLOR)
        if self.expanded:
            for line in self.lines:
                spaces = len(line) - len(line.lstrip())
                indent = " " * spaces
                clean_line = line.strip()
                if clean_line.startswith("|_"):
                    clean_line = clean_line[2:].strip()
                t.append(f"{indent}  |_ {clean_line}\n", style="gray50")
        return t
        
    def update(self):
        pass # Now handled automatically by Live in a background thread
        
    def stop(self):
        self.live.stop()
        
    def print_tree(self):
        if not self.lines: return
        
        elapsed_sec = time.time() - self.start_time
        model_str = f" · {self.model_name}" if self.model_name else ""
        console.print(f"\n[{ACCENT_COLOR}]✻ {self.title}... ({format_time(elapsed_sec)}{model_str})[/]")
        if self.expanded:
            for line in self.lines:
                spaces = len(line) - len(line.lstrip())
                indent = " " * spaces
                clean_line = line.strip()
                if clean_line.startswith("|_"):
                    clean_line = clean_line[2:].strip()
                console.print(f"{indent}  [{MUTED_COLOR}]|_ {clean_line}[/]")
        console.print("")
def print_turn_done(elapsed: float, tokens: int, tool_count: int):
    console.print(f"\n[{ACCENT_COLOR}]✔ Done[/] ({format_time(elapsed)} · ⛁ {tokens} tokens · {tool_count} tool calls)")
class LiveToolStream:
    def __init__(self):
        self.start_time = time.time()
        self.frames = ["○", "●"]
        self.content = ""
        self.tool_name = "Generating tool"
        self.live = Live(get_renderable=self.render, refresh_per_second=10, transient=True)
        
    def start(self):
        self.start_time = time.time()
        self.live.start()
        
    def update(self, raw_json_buffer: str):
        self.content = raw_json_buffer
        if '"name":' in raw_json_buffer:
            import re
            m = re.search(r'"name"\s*:\s*"([^"]+)"', raw_json_buffer)
            if m:
                self.tool_name = m.group(1)
        
    def render(self):
        from rich.console import Group
        from rich.panel import Panel
        elapsed_sec = time.time() - self.start_time
        frame_idx = int(elapsed_sec * 4) % len(self.frames)
        sym = self.frames[frame_idx]
        
        t = Text()
        t.append(f"\n{sym} {self.tool_name}... ({format_time(elapsed_sec)})\n", style="white bold")
        
        import re
        m = re.search(r'"(?:code|content|command|file_content)"\s*:\s*"(.*)', self.content, re.DOTALL)
        if m:
            preview = m.group(1)
            # Szybkie, naivowe odkodowanie by JSON wyglądał jak kod
            preview = preview.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            
            # Odcięcie końcówek json jeśli model go zamknął
            if preview.endswith('"\n}'): preview = preview[:-3]
            elif preview.endswith('"}'): preview = preview[:-2]
            elif preview.endswith('"'): preview = preview[:-1]
            
            lines = preview.splitlines()
            if len(lines) > 20:
                preview = "\n".join(lines[-20:])
                
            path_m = re.search(r'"(?:path|TargetFile|file_path|file)"\s*:\s*"([^"]+)"', self.content)
            title = f"[bold white]{path_m.group(1)}[/bold white]" if path_m else ""
            
            from rich import box
            panel = Panel(preview, border_style="white", box=box.ROUNDED, title=title, title_align="left")
            return Group(t, panel)
            
        return t
        
    def stop(self):
        self.live.stop()

class SearchSpinner:
    def __init__(self, query: str, is_web: bool = False):
        self.query = query
        self.is_web = is_web
        self.start_time = time.time()
        self.frames = ["⌕", "🌐"] if is_web else ["⌕"]
        self.live = Live(get_renderable=self.render, refresh_per_second=10, transient=True)
        
    def start(self):
        self.live.start()
        
    def render(self):
        elapsed = time.time() - self.start_time
        if self.is_web:
            frame_idx = int(elapsed / 0.6) % 2
            icon = self.frames[frame_idx]
            text = f"Web search: \"{self.query}\"..."
        else:
            icon = "⌕"
            text = f"Scanning: \"{self.query}\"..."
        
        t = Text()
        t.append(f"\n{icon} {text}", style="bold")
        return t
        
    def stop(self, result_summary: str, details: str = ""):
        self.live.stop()
        final_icon = "🌐" if self.is_web else "⌕"
        text = f"Web search: \"{self.query}\"" if self.is_web else f"Scanning: \"{self.query}\""
        
        console.print(f"\n[bold]{final_icon} {text}[/bold]")
        console.print(f"  [{MUTED_COLOR}]|_ {result_summary}[/]")
        if details:
            lines = [l for l in details.splitlines() if l.strip() and "Results for" not in l]
            if self.is_web:
                lines = [l for l in lines if "Link:" in l or l.startswith("http")]
            for line in lines[:5]:
                console.print(f"    [{MUTED_COLOR}]|_ {line}[/]")
            if len(lines) > 5:
                console.print(f"    [{MUTED_COLOR}]|_ ... and {len(lines) - 5} more[/]")
        
def render_todo(items: list, checked_indices: list):
    for i, item in enumerate(items):
        if i in checked_indices:
            console.print(f"[{SUCCESS_COLOR}]☑ {item}[/]")
        else:
            console.print(f"[{MUTED_COLOR}]☐ {item}[/]")
