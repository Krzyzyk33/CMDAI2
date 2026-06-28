import os
from typing import List, Dict, Any, Optional
SYSTEM_PROMPT = """You are CMDAI CODE, a highly capable AI coding assistant running locally in the terminal.
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
1. WRITE / CREATE: You can use these tools to create new files or completely OVERWRITE existing ones.
2. EDIT is only for existing files. You must provide the EXACT, literal `old_str` to replace. It must be unique.
3. EXECUTE ONLY ONE TOOL AT A TIME. Do not queue multiple tools in a single response. You must wait for the result of the first tool before calling the next one.
4. If you create or edit a python script, you must run it using the `run_python` tool to verify it works correctly.
5. FABLE 5 MODE: You are an autonomous agent. If you encounter an error, DO NOT GIVE UP. Analyze the error, try an alternative approach, and keep working indefinitely until the user's task is 100% completed. Never apologize and never stop halfway.
6. If the same tool call fails repeatedly, change your approach instead of repeating it.
7. NEVER run destructive commands (delete_file) without explicit user permission or unless asked to.
8. ALWAYS generate a short text response to the user AFTER finishing the entire task.
9. DO NOT write python scripts for web scraping or fetching APIs. Use `search_web` with the target URL directly instead.
10. CRITICAL: NEVER output code blocks directly in your conversational text response! If the user asks you to write code, you MUST use the `write_file` or `create_file` tool to save it to the disk. Your text response should only summarize what you saved.
11. CRITICAL: Writing "TOOL: <name>" inside the <think> block is ONLY for your planning. To ACTUALLY execute a tool, you MUST output the native JSON function calling payload! 
Your JSON MUST strictly follow this exact structure:
```json
{
  "name": "tool_name_here",
  "arguments": {
    "parameter_name": "value"
  }
}
```
Do not invent your own format (like omitting the "arguments" wrapper). You MUST use this exact structure to trigger the API.
12. CRITICAL: If the user request is extremely large, asks for a complete project, or you are starting a complex application, YOU MUST NOT attempt to write the entire code in one turn. In your first turn, you MUST use the 'submit_plan' tool to break the project down into multiple logical steps. Then wait, and implement the files ONE BY ONE in subsequent turns.
13. CRITICAL: You have NO LIMIT on file generation sizes. Whenever creating a file using `write_file`, ALWAYS output the 100% FULL and complete file, no matter how long it is. DO NOT split the code, do not create skeletons, and do not use `edit_file` immediately after. Just write the whole thing.
14. CRITICAL: You MUST ALWAYS invoke a tool immediately after closing the </think> tag! Do not just write text and stop. ALWAYS trigger the native JSON function call right after your thoughts end.
15. CRITICAL: You are STRICTLY FORBIDDEN from drawing ascii graphs, mermaid graphs, or any other visual representations in your text. 
16. CRITICAL: Your <think> block MUST ALWAYS use the tree structure (with `|_ `) exactly as shown in the example. This is mandatory for the UI to parse it into visual trees.
26: AVAILABLE TOOLS:
{tools_desc}
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
        path = os.path.join(self.session_manager.cmdai_code_dir, f"session_{self.session_manager.current_state.session_id}_history.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_history(self, session_id=None):
        import json
        if session_id:
            self.session_manager.load_state(session_id)
        
        path = os.path.join(self.session_manager.cmdai_code_dir, f"session_{self.session_manager.current_state.session_id}_history.json")
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
        cmdai_file = os.path.join(self.cwd, "CMDAI CODE.md")
        if os.path.exists(cmdai_file):
            with open(cmdai_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.system_prompt += f"\n\nPROJECT CONTEXT (CMDAI CODE.md):\n{content}"
    def _load_app_state(self) -> Dict[str, Any]:
        import json
        state_file = os.path.expanduser("~/.cmdai_code/state.json")
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _resolve_local_model_path(self, model_ref: str) -> Optional[str]:
        if not model_ref:
            return None

        expanded = os.path.expanduser(model_ref)
        candidates = []
        if os.path.isabs(expanded):
            candidates.append(expanded)
        else:
            candidates.append(os.path.abspath(expanded))
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates.append(os.path.join(app_dir, "systemmodels", expanded))
            candidates.append(os.path.join(app_dir, "models", expanded))

        for candidate in candidates:
            if os.path.exists(candidate) and candidate.lower().endswith(".gguf"):
                return candidate
        return None

    def _build_compaction_model(self, fallback_model):
        from .ui import console, MUTED_COLOR

        state = self._load_app_state()
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys_dir = os.path.join(app_dir, "systemmodels")
        model_ref = None
        
        # Zawsze najwyższy priorytet ma lokalny folder systemmodels
        if os.path.exists(sys_dir):
            import glob
            sys_models = glob.glob(os.path.join(sys_dir, "*.gguf"))
            if sys_models:
                needed_ctx = max(8192, self.get_token_count() + 4000)
                model_ref = {"path": sys_models[0], "n_ctx": needed_ctx, "n_gpu_layers": 8}
                
        # Jeżeli folder jest pusty, sprawdź czy użytkownik wybrał coś w UI (state.json)
        if not model_ref:
            model_ref = state.get("compaction_model")
        
        if not model_ref:
            return fallback_model, False

        try:
            if isinstance(model_ref, dict):
                local_path = self._resolve_local_model_path(
                    model_ref.get("path") or model_ref.get("model_path") or ""
                )
                if local_path:
                    from .llama import LlamaModel
                    base_ctx = int(model_ref.get("n_ctx", state.get("compaction_n_ctx", 8192)))
                    n_ctx = max(base_ctx, self.get_token_count() + 4000)
                    n_gpu_layers = int(model_ref.get("n_gpu_layers", state.get("compaction_n_gpu_layers", 8)))
                    return LlamaModel(local_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers), True

                if model_ref.get("name") and model_ref.get("base_url") is not None:
                    from .api_model import OpenAIAPIModel
                    return OpenAIAPIModel(
                        model_name=model_ref["name"],
                        api_key=model_ref.get("api_key", ""),
                        base_url=model_ref.get("base_url", ""),
                        provider_id=model_ref.get("provider")
                    ), True

            if isinstance(model_ref, str):
                local_path = self._resolve_local_model_path(model_ref)
                if local_path:
                    from .llama import LlamaModel
                    base_ctx = int(state.get("compaction_n_ctx", 8192))
                    n_ctx = max(base_ctx, self.get_token_count() + 4000)
                    n_gpu_layers = int(state.get("compaction_n_gpu_layers", 8))
                    return LlamaModel(local_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers), True

                for api_model in state.get("api_models", []):
                    if api_model.get("name") == model_ref:
                        from .api_model import OpenAIAPIModel
                        return OpenAIAPIModel(
                            model_name=api_model["name"],
                            api_key=api_model.get("api_key", ""),
                            base_url=api_model.get("base_url", ""),
                            provider_id=api_model.get("provider")
                        ), True

            console.print(f"[yellow][Compaction model not found: {model_ref}. Using current model.][/]")
        except Exception as e:
            console.print(f"[yellow][Could not load compaction model: {e}. Using current model.][/]")

        return fallback_model, False

    def _fallback_summary(self) -> str:
        recent = []
        for msg in self.messages[-8:]:
            content = msg.get("content", "")
            if len(content) > 800:
                content = content[:800] + "..."
            recent.append(f"- {msg.get('role', 'unknown')}: {content}")

        return (
            "Goal: Continue the current session after automatic context compaction.\n"
            "Decisions:\n"
            "- Automatic summarization failed; an emergency fallback summary of recent messages was preserved.\n"
            "Files:\n"
            "- none: no reliable changelog available in fallback summary.\n"
            "Plan:\n"
            "[ ] Continue from the latest user request, utilizing the recent messages below.\n"
            "Issues:\n"
            "- The summary was generated by a fallback without semantic compression.\n"
            "Constraints:\n"
            "- Do not assume facts that are not present in this summary.\n\n"
            "Recent messages:\n" + "\n".join(recent)
        )

    def trigger_compaction(self, model):
        from .ui import console, MUTED_COLOR, ThinkingTree
        if not self.messages:
            return

        compaction_prompt = (
            "You are an AI tasked with summarizing the current coding session. Read the history and summarize it precisely in English. Use EXACTLY this markdown format, without code fences and without extra headings:\n\n"
            "Goal: <1-2 lines with the user's current goal>\n"
            "Decisions:\n"
            "- <important decision>\n"
            "Files:\n"
            "- <file path>: <what changed or why it matters>\n"
            "Plan:\n"
            "[x] <completed step>\n"
            "[ ] <next step to do>\n"
            "Issues:\n"
            "- <open issue, error, failed command, missing test, or blocker>\n"
            "Constraints:\n"
            "- <important constraint or latest user instruction>\n\n"
            "CRITICAL: Keep the summary extremely compact. Your output MUST NOT exceed 2000 tokens (approx. 8000 characters). "
            "Answer ONLY with the requested format in English."
        )
        compaction_sys = "You are a memory-compression AI. You must read the history and output ONLY a summary in the exact requested format. You DO NOT use tools. Do NOT generate JSON tool calls under any circumstances."
        messages = [{"role": "system", "content": compaction_sys}] + self.messages + [{"role": "user", "content": compaction_prompt}]

        from .ui import console, MUTED_COLOR, ThinkingTree
        tree = ThinkingTree(expanded=True, simulate=True, title="Loading system model", model_name="background task")
        tree.start()

        compaction_model_instance, should_release = self._build_compaction_model(model)
        main_model_released = False
        if should_release and compaction_model_instance is not model:
            try:
                if hasattr(model, "unload"):
                    model.unload()
                if hasattr(model, "_llm") and getattr(model, "_llm", None) is not None:
                    model._llm = None
                    import gc
                    gc.collect()
                main_model_released = True
            except Exception:
                pass

        model_name_str = getattr(compaction_model_instance, "model_name", "system model")
        import os
        model_name_str = os.path.basename(model_name_str)
        
        tree.title = "Summarizing"
        tree.model_name = model_name_str
        
        max_retries = 3
        retry_count = 0
        current_messages = self.messages[:]
        
        while retry_count < max_retries:
            messages = [{"role": "system", "content": compaction_sys}] + current_messages + [{"role": "user", "content": compaction_prompt}]
            response_text = ""
            current_line = ""
            try:
                for content, thinking, _ in compaction_model_instance.stream_chat(messages, reasoning_budget=0):
                    chunk = content or thinking or ""
                    if chunk:
                        if len(response_text) > 9000:  # Hard limit ~2000 tokenów na wypadek halucynacji
                            break
                        response_text += chunk
                        current_line += chunk
                        if '\n' in current_line:
                            parts = current_line.split('\n')
                            for p in parts[:-1]:
                                if p.strip():
                                    tree.add_line(p)
                            current_line = parts[-1]
                if current_line.strip():
                    tree.add_line(current_line)
                break  # Sukces!
            except Exception as e:
                err_str = str(e).lower()
                if "exceed" in err_str or "context" in err_str or "token" in err_str or "capacity" in err_str:
                    retry_count += 1
                    if retry_count < max_retries:
                        console.print(f"\n[{MUTED_COLOR}][Model systemowy nie pomieścił tej porcji danych. Odcinam 30% najstarszej historii i próbuję ponownie ({retry_count}/3)...][/]")
                        cut_idx = max(1, int(len(current_messages) * 0.3))
                        current_messages = current_messages[cut_idx:]
                        continue
                
                tree.stop()
                console.print(f"[yellow][Compaction failed: {e}. Using emergency summary.][/]")
                response_text = self._fallback_summary()
                break
                
        tree.stop()
        if should_release:
            try:
                if hasattr(compaction_model_instance, "_llm"):
                    compaction_model_instance._llm = None
                    import gc
                    gc.collect()
                if hasattr(compaction_model_instance, "unload"):
                    compaction_model_instance.unload()
            except Exception:
                pass

        response_text = response_text.strip() or self._fallback_summary()

        from .session import SessionState
        self.session_manager.current_state = SessionState.from_markdown(response_text, self.session_manager.current_state.session_id)
        self.session_manager.save_state()
        self.messages = [{
            "role": "user",
            "content": (
                "[COMPRESSED SESSION CONTEXT]\n"
                f"{self.session_manager.current_state.to_prompt() or response_text}\n\n"
                "Kontynuuj od tego miejsca. To jest streszczenie poprzedniej historii po kompresji kontekstu."
            )
        }]
        self.save_history()
        tokens_count = len(response_text) // 4
        console.print(f"[{MUTED_COLOR}][Context compacted: ~{tokens_count} tokens summary saved.][/]")
        if main_model_released:
            console.print(f"[{MUTED_COLOR}][Main model will reload on the next turn.][/]")
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
        sys_msg = self.get_system_message("", "auto", "")
        total_chars = len(sys_msg.get("content", "")) + 4000 # 4000 zapasu na narzędzia (tools_desc) i tagi myślenia
        for msg in self.messages:
            total_chars += len(msg.get("content", ""))
        # Ekstremalnie bezpieczny dzielnik dla polskiego tekstu i gęstego kodu (1 token = ~2 znaki)
        return total_chars // 2
        
    def clear(self):
        self.messages = []
        self.save_history()
        
    def count_tokens(self) -> int:
        # Pomiń system prompt, żeby pasek zaczynał od 0% (pokazujemy zużycie "rozmową")
        text = " ".join([m.get("content", "") for m in self.messages if m.get("content")])
        words = len(text.split())
        return int(words * 1.3)
