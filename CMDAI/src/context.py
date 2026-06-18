import os
from typing import List, Dict
SYSTEM_PROMPT = """You are CMDAI2, a highly capable AI coding assistant running locally in the terminal.
You have access to tools to read, create, edit, search and delete files. You CAN run terminal commands and bash/powershell scripts using the bash tool, but ONLY under user supervision (the user must confirm execution).
Read the *** THINKING LEVEL REQUIREMENTS *** at the end of this prompt carefully. IF your current thinking level requires a <think> block, you must output your internal thinking process between <think> and </think> tags.
If you DO generate a <think> block, you MUST ALWAYS use a hierarchical tree structure with `|_ ` for indentation so the UI can parse your thinking.
Example:
<think>
  |_ UNDERSTAND: Analizuję zapytanie użytkownika...
  |_ CONTEXT:
    |_ Sprawdzam strukturę projektu
    |_ Narzędzia są gotowe
  |_ PLAN: Wykonanie zadania
</think>
HARD RULES FOR TOOLS & THINKING:
1. WRITE is only for new files. Check if it exists first.
2. EDIT is only for existing files. You must provide the EXACT, literal `old_str` to replace. It must be unique.
3. EXECUTE ONLY ONE TOOL AT A TIME. Do not queue multiple tools in a single response. You must wait for the result of the first tool before calling the next one.
4. If you create or edit a python script, you must run it using the `run_python` tool to verify it works correctly.
5. FABLE 5 MODE: You are an autonomous agent. If you encounter an error, DO NOT GIVE UP. Analyze the error, try an alternative approach, and keep working indefinitely until the user's task is 100% completed. Never apologize and never stop halfway.
6. If the same tool call fails repeatedly, change your approach instead of repeating it.
7. NEVER run destructive commands (delete_file) without explicit user permission or unless asked to.
8. ALWAYS generate a short text response to the user AFTER finishing the entire task.
9. DO NOT write python scripts for web scraping or fetching APIs. Use `search_web` with the target URL directly instead.
10. CRITICAL: NEVER output code blocks directly in your conversational text response! If the user asks you to write code, you MUST use the `write_file` or `create_file` tool to save it to the disk. Your text response should only summarize what you saved.
11. CRITICAL: Writing "TOOL: <name>" inside the <think> block is ONLY for your planning. To ACTUALLY execute a tool, you MUST output the native JSON function calling payload! Never just write the text and stop. You MUST trigger the API's function call mechanism.
12. CRITICAL: If the user request is extremely large, asks for a complete project, or you are starting a complex application, YOU MUST NOT attempt to write the entire code in one turn. In your first turn, you MUST use the 'submit_plan' tool to break the project down into multiple logical steps. Then wait, and implement the files ONE BY ONE in subsequent turns.
13. CRITICAL: If you hit the max_tokens limit and get cut off while outputting a JSON tool call for 'write_file', DO NOT try to write the entire massive file again! Instead, use 'write_file' to create only a small structural skeleton of the file, and then use 'edit_file' in subsequent turns to append the remaining content section by section.
14. CRITICAL: You MUST ALWAYS invoke a tool immediately after closing the </think> tag! Do not just write text and stop. ALWAYS trigger the native JSON function call right after your thoughts end.
15. CRITICAL: You are STRICTLY FORBIDDEN from drawing ascii graphs, mermaid graphs, or any other visual representations in your text. 
16. CRITICAL: Your <think> block MUST ALWAYS use the tree structure (with `|_ `) exactly as shown in the example. This is mandatory for the UI to parse it into visual trees.
26: AVAILABLE TOOLS:
{tools_desc}
UI FORMATTING RULES:
You must include the following formatted blocks in your response text to inform the user about the operations you perform. Use ONLY real data. If an operation wasn't performed yet, do NOT generate its block.

1. Read (reading a file)
Format:
● Read: <file_name>
  ⎿ <N> lines
When to generate: after reading a file (e.g. read_file).
Data required: file name, number of lines in the read file.

2. Edit (editing an existing file)
Format:
● Edit: <file_name>
  ⎿ Changed <file_name> (+<N> / -<M>)
     <line_number>   <unchanged_line_content>
     <line_number> - <deleted_line_content>
     <line_number> + <added_line_content>
When to generate: when editing an existing file (e.g. edit_file). Must be preceded by reading.
Data required: file name, number of added (+N) and deleted (-M) lines, content of changes (like diff).

3. Write (new file)
Format:
● New file: <file_name>
  ⎿ Created <file_name> (<N> lines)
     1  <first_line>
     2  <second_line>
     3  <third_line>
When to generate: when creating a new file. Do not overwrite existing files with this action!
Data required: file name, total number of lines, preview of the first 3 lines.

4. Bash (executing a command)
Success format:
● Command: <command>
  ⎿ OK (exit 0)
Error format:
● Command: <command>
  ⎿ ✗ <error_content> (exit <code_number>)
When to generate: after executing a command in the terminal. Always provide the real exit code.
If a command fails 3 times in a row, STOP and ask the user.

5. Search / Grep / Glob (searching)
Format with results:
● Search: "<pattern>"
  ⎿ <N> results
     <file1>:<line>
     <file2>:<line>
Format without results:
● Search: "<pattern>"
  ⎿ no results
When to generate: after using search tools. Provide up to 5 results.

6. TodoWrite (task plan)
Format:
● Task Plan
  ⎿ [x] <completed_task>
    [ ] <task_to_do>
When to generate: at the start of a task (min. 3 steps). Update the widget in subsequent responses.

7. Permission Prompt (asking for consent)
Format:
● Command: <command>
  Execute?
  ❯ 1. Yes
    2. Yes, don't ask again for "<command_type>"
    3. No - tell what to do instead
When to generate: BEFORE a potentially destructive command (rm, git push --force, install). Wait for user's choice.

8. Task / Subagent dispatch
Format:
● Task: <short_description>
  ⎿ Done (<N> actions • <K>k tokens • <T>s)
When to generate: when delegating a larger batch of tasks.

9. Status bar (turn status bar)
While working it is automatically at the bottom of the screen: ✻ Working... (<T>s • esc = abort)
At the end: ✻ Done (<T>s • <K>k tokens • <N> actions • esc = abort)

REMEMBER: Always generate these blocks based on actual tool results, DO NOT INVENT them in advance.
CRITICAL COMMUNICATION RULE: Always respond to the user in their own language (e.g., Polish) when writing conversational text!
"""
class ContextManager:
    def __init__(self, cwd: str = ".", session_id: str = None):
        self.cwd = os.path.abspath(cwd)
        self.messages: List[Dict[str, str]] = []
        self.system_prompt = SYSTEM_PROMPT
        
        from .session import SessionManager
        self.session_manager = SessionManager(cwd)
        
        if session_id:
            self.session_manager.load_state(session_id)
        else:
            import datetime
            new_id = "czat_" + datetime.datetime.now().strftime("%d%m_%H%M%S")
            self.session_manager.load_state(new_id)
            
        self.load_history()
        
        self._load_project_context()
    def save_history(self):
        import json
        self.session_manager.ensure_dir()
        path = os.path.join(self.session_manager.cmdai2_dir, f"session_{self.session_manager.current_state.session_id}_history.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_history(self, session_id=None):
        import json
        if session_id:
            self.session_manager.load_state(session_id)
        
        path = os.path.join(self.session_manager.cmdai2_dir, f"session_{self.session_manager.current_state.session_id}_history.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.messages = json.load(f)
            except Exception:
                self.messages = []
        else:
            self.messages = []
            
    def rename_session(self, new_id: str):
        self.session_manager.rename_session(new_id)
        self.save_history()

    def _load_project_context(self):
        cmdai_file = os.path.join(self.cwd, "CMDAI2.md")
        if os.path.exists(cmdai_file):
            with open(cmdai_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.system_prompt += f"\n\nPROJECT CONTEXT (CMDAI2.md):\n{content}"
    def trigger_compaction(self, model):
        from .ui import console, MUTED_COLOR
        console.print(f"\n[{MUTED_COLOR}][Compacting context memory...][/]")
        compaction_prompt = "Summarize this working session precisely in this markdown format (without surrounding tags):\nGoal: <1-2 lines>\nDecisions:\n- <decision>\nFiles:\n- <file>: <change>\nPlan:\n[x] <completed step>\n[ ] <step to do>\nIssues:\n- <issue>\nConstraints:\n- <constraint>"
        messages = self.messages + [{"role": "user", "content": compaction_prompt}]
        
        response_text = ""
        for _, content, _ in model.stream_chat(messages, reasoning_budget=0):
            if content:
                response_text += content
                
        from .session import SessionState
        self.session_manager.current_state = SessionState.from_markdown(response_text, self.session_manager.current_state.session_id)
        self.session_manager.save_state()
        self.messages = []
    def get_system_message(self, tools_desc: str, mode: str, thinking_desc: str) -> Dict[str, str]:
        prompt = self.system_prompt
        
        # Baza informacji o narzędziach
        if tools_desc:
            prompt += f"\n\nAVAILABLE TOOLS:\n{tools_desc}\nCRITICAL: Use the tools directly. DO NOT ask the user to run commands for you."
        # Różne zachowanie w zależności od trybu
        if mode == "plan":
            prompt += (
                "\n\n*** CRITICAL: YOU ARE IN PLAN MODE ***\n"
                "Your ONLY objective is to analyze the user's request and write a detailed architecture and execution plan into a file named `plan.md`.\n"
                "1. YOU ARE STRICTLY FORBIDDEN from creating or editing any code files (.py, .js, .html, etc.).\n"
                "2. You may use read tools (read_file, list_dir, grep) to explore the codebase.\n"
                "3. Once you understand the task, use write_file/create_file ONLY to save your plan to `plan.md`.\n"
                "4. Do NOT attempt to implement the code yourself in this mode."
            )
        elif mode == "code":
            prompt += (
                "\n\n*** CURRENT MODE: CODE MODE ***\n"
                "You are an expert developer. You must write, edit, and fix code based on the user's instructions.\n"
                "1. If a `plan.md` exists, follow it step by step.\n"
                "2. When writing code, write complete, robust, and clean code.\n"
                "3. The user will be asked to accept your code changes before they are saved to disk."
            )
        elif mode == "auto":
            prompt += (
                "\n\n*** CURRENT MODE: AUTO MODE ***\n"
                "You are a fully autonomous AI agent. You have permission to create, edit, and run code without user confirmation.\n"
                "1. Analyze the objective, plan your steps, and execute them automatically.\n"
                "2. You can use bash to test your code and fix errors autonomously.\n"
                "3. Continue working until the task is completely finished."
            )
        # Plan.md context injection
        plan_file = os.path.join(self.cwd, "plan.md")
        if os.path.exists(plan_file):
            try:
                with open(plan_file, "r", encoding="utf-8") as f:
                    plan_content = f.read()
                    prompt += f"\n\nCURRENT PLAN INJECTED (plan.md):\n{plan_content}\nAlways refer to this plan when deciding what to do next."
            except Exception:
                pass
                
        # Session context injection
        session_context = self.session_manager.current_state.to_prompt()
        if session_context:
            prompt += f"\n\n{session_context}"
            
        if thinking_desc:
            prompt += (
                f"\n\n*** THINKING LEVEL REQUIREMENTS ***\n"
                f"{thinking_desc}\n\n"
                "CRITICAL INSTRUCTION: Read the rules above. IF your current thinking level requires thoughts, your output MUST begin with a <think>...</think> block analyzing the problem according to the requirements above.\n"
                "If you are instructed to use Text-Based Tool Calling, you MUST output your tool call as a JSON block immediately after the </think> tag, like this:\n"
                "```json\n{\n  \"name\": \"tool_name\",\n  \"arguments\": { ... }\n}\n```\n"
                "Do NOT output native API tool calls if they are disabled. Always write <think> before your json block!\n"
                "EXTREMELY IMPORTANT: YOU MUST ALWAYS USE A NATIVE JSON TOOL CALL IN YOUR RESPONSE. NEVER RESPOND WITH JUST TEXT IF THE USER ASKS YOU TO DO SOMETHING!"
            )
        return {"role": "system", "content": prompt}
    def add_user_message(self, msg: str):
        self.messages.append({"role": "user", "content": msg})
        self.save_history()
    def add_assistant_message(self, msg: str, tool_calls=None):
        m = {"role": "assistant", "content": msg}
        if tool_calls:
            # Upewnij się, że arguments są zawsze stringiem, co jest wymagane przez API OpenAI
            formatted_tc = []
            import json
            for tc in tool_calls:
                new_tc = tc.copy()
                if "function" in new_tc and isinstance(new_tc["function"].get("arguments"), dict):
                    new_tc["function"] = new_tc["function"].copy()
                    new_tc["function"]["arguments"] = json.dumps(new_tc["function"]["arguments"])
                formatted_tc.append(new_tc)
            m["tool_calls"] = formatted_tc
        self.messages.append(m)
        self.save_history()
    def add_tool_message(self, tool_call_id: str, name: str, content: str):
        # Format explicitly as a user message to bypass llama-cpp-python template limitations
        self.messages.append({
            "role": "user",
            "content": f"<tool_response>\n{content}\n</tool_response>"
        })
        self.save_history()
    def get_messages(self, tools_desc: str = "", mode: str = "auto", thinking_desc: str = "") -> List[Dict[str, str]]:
        sys_msg = self.get_system_message(tools_desc, mode, "")
        msgs = list(self.messages)
        
        if thinking_desc and msgs:
            last = dict(msgs[-1])
            injection = (
                f"\n\n*** CURRENT THINKING LEVEL REQUIREMENTS ***\n"
                f"{thinking_desc}\n\n"
                "CRITICAL INSTRUCTION: Read the rules above. IF your current thinking level requires thoughts, your output MUST begin with a <think>...</think> block analyzing the problem according to the requirements above.\n"
                "If you are instructed to use Text-Based Tool Calling, you MUST output your tool call as a JSON block immediately after the </think> tag, like this:\n"
                "```json\n{\n  \"name\": \"tool_name\",\n  \"arguments\": { ... }\n}\n```\n"
                "Do NOT output native API tool calls if they are disabled. Always write <think> before your json block!\n"
                "EXTREMELY IMPORTANT: YOU MUST ALWAYS USE A NATIVE JSON TOOL CALL IN YOUR RESPONSE. NEVER RESPOND WITH JUST TEXT IF THE USER ASKS YOU TO DO SOMETHING!"
            )
            
            if last["role"] == "user":
                last["content"] += injection
                msgs[-1] = last
            else:
                msgs.append({"role": "user", "content": injection.strip()})
        elif thinking_desc:
            # Fallback jeśli nie ma jeszcze wiadomości
            sys_msg["content"] += f"\n\n*** CURRENT THINKING LEVEL REQUIREMENTS ***\n{thinking_desc}"
            
        return [sys_msg] + msgs
        
    def get_token_count(self) -> int:
        total_chars = len(self.system_prompt)
        for msg in self.messages:
            total_chars += len(msg.get("content", ""))
        return total_chars // 4
        
    def clear(self):
        self.messages = []
        self.save_history()
        
    def count_tokens(self) -> int:
        # Pomiń system prompt, żeby pasek zaczynał od 0% (pokazujemy zużycie "rozmową")
        text = " ".join([m.get("content", "") for m in self.messages if m.get("content")])
        words = len(text.split())
        return int(words * 1.3)
