import os
import json
from .llama import LlamaModel
from .context import ContextManager
from .ui import print_user_msg, print_agent_msg, print_tool_call, print_tool_result, print_diff, print_code_panel, ThinkingTree, console
from .tools import TOOLS_DEFINITIONS, execute_tool

class Agent:
    def __init__(self, model: LlamaModel, context: ContextManager):
        self.model = model
        self.context = context
        self.max_iterations = 25
        self.auto_review = False
        
    def get_tool_desc(self) -> str:
        desc = ""
        for t in TOOLS_DEFINITIONS:
            f = t["function"]
            desc += f"- {f['name']}: {f['description']}\n"
        return desc
        
    def handle_user_input(self, user_msg: str, mode: str, input_handler):
        import time
        from .ui import print_turn_done
        
        # 8k Engine: Automatyczne zarządzanie rozmiarem kontekstu (90% maksymalnego okna)
        if self.context.get_token_count() >= self.model.get_context_limit() * 0.9:
            self.context.trigger_compaction(self.model)
            
        self.context.add_user_message(user_msg)
        
        self._has_reflected = False
        turn_start = time.time()
        total_tools = 0
        iteration = 0
        modified_files = set()
        self._fable_tested = False
        while iteration < self.max_iterations:
            iteration += 1
            tree = ThinkingTree(expanded=input_handler.thinking_expanded)
            tree.start()
            
            level_info = input_handler.thinking_levels[input_handler.thinking_idx]
            level_idx = input_handler.thinking_idx
            
            if level_idx == 0:
                thinking_desc = "IF you generate thoughts, you MUST wrap them inside <think> and </think> tags.\nTHINKING BEHAVIOR - LOW:\nDo not generate a THINK section. Proceed directly to ACTION or text response.\nException: if the task requires choosing a file/function to edit and it is not obvious from the user's prompt, write only:\n<think>\n  |_ UNDERSTAND: <what the task is about>\n  |_ PLAN: <1 line>\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nAfter performing an action, DO NOT generate THINK, regardless of the result.\nException: if Bash returned an error, write 1 line of diagnosis in <think> and immediately propose a fix in the next ACTION.\nDo not perform additional 'just in case' actions (build, search) unless the user asked for it.\nCRITICAL: ALWAYS respond to the user in their own language (e.g., Polish)."
            elif level_idx == 1:
                thinking_desc = "IF you generate thoughts, you MUST wrap them inside <think> and </think> tags.\nTHINKING BEHAVIOR - MEDIUM:\nAt the beginning of the turn, generate a concise THINK strictly inside <think> and </think> tags:\n<think>\n  |_ UNDERSTAND: <what the task is about>\n  |_ PLAN: <short list of steps (max 3)>\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nDo not generate sub-trees.\nAfter reading/searching, DO NOT generate THINK, unless the result differs drastically from expectations.\nAfter modifying actions (Edit/Write/Bash), you may generate a short THINK (1-2 lines) if the plan needs updating.\n\nForced actions: Search all callers after changing a function signature (ACTION: Search). Do not build the project unless requested.\nCRITICAL: ALWAYS respond to the user in their own language (e.g., Polish)."
            elif level_idx == 2:
                thinking_desc = "IF you generate thoughts, you MUST wrap them inside <think> and </think> tags.\nTHINKING BEHAVIOR - HIGH:\nAt the beginning of the turn, generate a structured THINK strictly inside <think> and </think> tags:\n<think>\n  |_ UNDERSTAND: <what the task is about>\n  |_ OPTIONS: <option A> | <option B> (only for complex or ambiguous problems)\n  |_ CHOICE: <chosen option + brief justification>\n  |_ PLAN: <numbered list of steps>\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nUse sub-trees (indented lists) only for significant architectural decisions.\nAfter key actions, generate a short THINK confirming status:\n<think>\n  |_ CONFIRMATION: <status + next step>\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nForced actions: ALWAYS search callers after changing a function signature. ALWAYS run a build after a block of related code edits.\nCRITICAL: ALWAYS respond to the user in their own language (e.g., Polish)."
            elif level_idx == 3:
                thinking_desc = "IF you generate thoughts, you MUST wrap them inside <think> and </think> tags.\nTHINKING BEHAVIOR - ULTRA:\nAt the beginning of EACH turn, generate a THINK strictly inside <think> and </think> tags:\n<think>\n  |_ UNDERSTAND: <what the task is about>\n  |_ CONTEXT: <what you already know from previous actions>\n  |_ OPTIONS: <option A> | <option B>\n  |_ CHOICE: <chosen option + justification>\n  |_ RISK: <potential problem + mitigation>\n  |_ PLAN: <numbered list of steps>\n\nFor EACH PLAN point that has more than one execution method, write a sub-tree:\n    |_ <plan point>\n      |_ > option 1\n      |_ > option 2\n      |_ > choice + justification\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nAfter EACH action, generate a new THINK:\n<think>\n  |_ CONFIRMATION: <did the result match expectations? what next?>\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nForced actions: ALWAYS search callers after changing a signature. ALWAYS run a build after editing code.\nCRITICAL: ALWAYS respond to the user in their own language (e.g., Polish)."
            elif level_idx == 4:
                thinking_desc = "IF you generate thoughts, you MUST wrap them inside <think> and </think> tags.\nTHINKING BEHAVIOR - EXTREME:\nAt the beginning of EACH turn, analyze the entire project. Generate an exhaustive THINK strictly inside <think> and </think> tags:\n<think>\n  |_ UNDERSTAND: <what the task is about on a project scale>\n  |_ CONTEXT: <conclusions from logs, file structures, and architecture>\n  |_ OPTIONS: <extensive list of options and paths>\n  |_ CHOICE: <final choice + impact on other modules>\n  |_ RISK: <detailed list of edge cases, security, and performance>\n  |_ PLAN: <very detailed list of steps>\n\nFor EACH PLAN point, you must write a multi-level sub-tree. In the first iteration, you MUST use the 'submit_plan' tool.\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nAfter EACH action, perform a deep evaluation:\n<think>\n  |_ EVALUATION: <detailed analysis of the returned result, error diagnosis, plan corrections>\n  |_ NEXT_ACTION: <what you will do next, or 'none' if task is fully complete>\n</think>\n\nForced actions: ALWAYS search all dependencies. ALWAYS run build and unit tests after EACH file edit. Perform a re-validation procedure at the end.\nCRITICAL: ALWAYS respond to the user in their own language (e.g., Polish)."

            thinking_desc += f"\n\nCRITICAL: Your THINKING TOKEN BUDGET is exactly {level_info[1]} tokens. If you feel you have only 10% of your thinking capacity left, you MUST IMMEDIATELY stop planning, close the <think> block, and output the JSON tool call! Never run out of tokens before generating the tool.\nCRITICAL: NEVER write 'TOOL: None' unless you are absolutely 100% finished with the user's task and have no code left to write. If the user asks for code, you MUST use a tool (e.g. write_file)!\nCRITICAL: Writing 'TOOL: <name>' in your thought block is NOT enough. You MUST actually trigger the native JSON function calling mechanism immediately after closing the <think> block!"
            
            messages = self.context.get_messages(self.get_tool_desc(), thinking_desc=thinking_desc)
            
            # Filtrowanie narzędzi
            if mode == "plan":
                allowed_tools = ["read_file", "list_dir", "grep", "search_web", "save_plan"]
                filtered_tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in allowed_tools]
            else:
                disallowed_tools = ["save_plan"]
                if level_idx >= 3 and iteration == 1:
                    allowed = ["read_file", "list_dir", "grep", "search_web", "submit_plan"]
                    filtered_tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in allowed]
                else:
                    if level_idx < 3:
                        disallowed_tools.append("submit_plan")
                    filtered_tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] not in disallowed_tools]
            
            use_native_tools = (level_idx == 0)
            if not use_native_tools:
                messages[0]["content"] += "\n\nCRITICAL: You are configured to use TEXT-BASED TOOL CALLING. You MUST NOT use native function calling. Output your tool call as a JSON markdown block after your <think> block."
                passed_tools = None
            else:
                passed_tools = filtered_tools
                
            try:
                if hasattr(self.model, "llm"):
                    _ = self.model.llm
                stream = self.model.stream_chat(messages, tools=passed_tools, reasoning_budget=level_info[1])
            except Exception as e:
                console.print(f"\n[red bold]Błąd ładowania modelu: {e}[/red bold]\n[yellow]Wpisz /model aby zmienić na poprawny model![/yellow]")
                return
                
            full_content = ""
            full_thinking = ""
            tool_calls = None
            thinking_newline = True
            
            in_thinking_tree = False
            thinking_buffer = ""
            
            plan_finished = False
            line_buffer = ""
            first_line_checked = False
            in_plan = False
            tool_detected = False
            printed_idx = 0
            content_to_print = ""
            tree_printed = False
            
            try:
                esc_count = 0
                import os
                if os.name == "nt":
                    import msvcrt
                
                for content, thinking, tc in stream:
                    if os.name == "nt" and msvcrt.kbhit():
                        while msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key == b'\x1b':
                                esc_count += 1
                            else:
                                esc_count = 0
                        if esc_count >= 2:
                            from rich.console import Console
                            Console().print("\n\n[red bold][Generowanie przerwane przez klawisz ESC][/red bold]\n")
                            break
                            
                    if content:
                        full_content += content
                        if not tool_detected:
                            raw = full_content.lstrip()
                            if raw.startswith("{") or raw.startswith("`") or raw.startswith("n") or raw.startswith("o"):
                                # Prawdopodobnie blok JSON lub tool call - wstrzymaj drukowanie
                                pass
                            else:
                                chunk = full_content[printed_idx:]
                                if chunk:
                                    if tree.live.is_started:
                                        tree.stop()
                                        console.print() # nowa linia po drzewie
                                    import sys
                                    console.print(chunk, end="")
                                    sys.stdout.flush()
                                    printed_idx = len(full_content)
                                    
                    if thinking:
                        full_thinking += thinking
                        for char in thinking:
                            thinking_buffer += char
                            if char == '\n':
                                if thinking_buffer.strip():
                                    tree.add_line(thinking_buffer.rstrip('\n'))
                                thinking_buffer = ""
                                
                    if tc:
                        tool_detected = True
                        tool_calls = tc
            
                # Opróżnienie bufora jeśli strumień się skończył a to nie było narzędzie
                if not tool_detected and printed_idx < len(full_content):
                    content_to_print += full_content[printed_idx:]
                    printed_idx = len(full_content)
                    
            except Exception as e:
                error_str = str(e)
                if "exceed context window" in error_str:
                    console.print(f"\n[red bold]Błąd: Przepełniono pamięć kontekstu (za dużo tekstu): {error_str}[/red bold]\n[yellow]Wyczyść historię wpisując komendę /clear, lub skróć swój ostatni prompt.[/yellow]")
                else:
                    console.print(f"\n[red bold]Krytyczny błąd silnika podczas generowania: {error_str}[/red bold]\n[yellow]Najprawdopodobniej brakło pamięci VRAM (Out Of Memory) lub format modelu nie jest do końca wspierany.[/yellow]")
                return
            finally:
                if thinking_buffer.strip():
                    tree.add_line(thinking_buffer.strip())
                tree.stop()
                
            if not tool_calls:
                # Fallback: check if the model hallucinated raw JSON tool calls
                raw = full_content.strip()
                import re
                
                # Extract markdown json blocks
                json_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
                if json_blocks:
                    mock_calls = []
                    for block in json_blocks:
                        try:
                            parsed = json.loads(block)
                            if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                                mock_calls.append({"id": "call_mock", "type": "function", "function": parsed})
                        except json.JSONDecodeError:
                            pass
                    if mock_calls:
                        tool_calls = mock_calls
                else:
                    # Extract outermost braces
                    match = re.search(r'\{.*\}', raw, re.DOTALL)
                    if match:
                        raw = match.group(0)
                        try:
                            parsed = json.loads(raw)
                            if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                                tool_calls = [{"id": "call_mock", "type": "function", "function": parsed}]
                        except json.JSONDecodeError:
                            pass
                    # If that fails, try finding multiple JSON objects (e.g. {}{})
                    blocks = re.split(r'}\s*{', raw)
                    mock_calls = []
                    for i, b in enumerate(blocks):
                        if i > 0: b = "{" + b
                        if i < len(blocks) - 1: b = b + "}"
                        try:
                            parsed = json.loads(b)
                            if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                                mock_calls.append({"id": "call_mock", "type": "function", "function": parsed})
                        except json.JSONDecodeError:
                            pass
                    if mock_calls:
                        tool_calls = mock_calls
                        full_content = ""

            # Self-Correction Loop for missing thinking, empty response or silent thinking
            if not full_content.strip() and not tool_calls:
                if not full_thinking.strip():
                    console.print("\n[yellow]⚠️ Model generated completely empty response. Retrying (self-correction)...[/yellow]")
                    self.context.add_user_message("System Error: You returned an empty response. Remember to generate a <think> block (if required) and take action or provide a text response.")
                else:
                    console.print("\n[yellow]⚠️ Model only generated thinking but took no action (likely hit token limit). Retrying (self-correction)...[/yellow]")
                    self.context.add_user_message("System Error: You generated a very long <think> block and stopped abruptly, likely hitting the max token limit. You MUST now use a tool (e.g. write_file) immediately to continue your work! Limit your thinking to 1 sentence and output the tool call.")
                continue

            if level_idx > 0 and not full_thinking.strip() and not ("<think>" in full_content):
                console.print("\n[yellow]⚠️ Model ignored the thinking requirement. Retrying (self-correction)...[/yellow]")
                self.context.add_assistant_message(full_content)
                self.context.add_user_message("System Error: You broke the rules. You must generate a <think>...</think> block with analysis before using a tool or sending a response. Try again.")
                continue

            # if not tree_printed:
            #    tree.print_tree()

            if not tool_calls:
                import re
                tool_match = re.search(r"NEXT_ACTION:\s*(.*)", full_thinking, re.IGNORECASE)
                if tool_match and tool_match.group(1).strip().lower() != "none" and tool_match.group(1).strip().lower() != "'none'":
                    action_text = tool_match.group(1).strip()
                    console.print(f"\n[yellow]⚠️ Model planned next action: '{action_text}' but failed to invoke a tool. Retrying (self-correction)...[/yellow]")
                    self.context.add_assistant_message(full_content)
                    self.context.add_user_message(f"System Error: You planned the following action in your thinking block: '{action_text}', but you FAILED to output any JSON function call payload. You MUST output the appropriate native JSON tool call now to execute this action.")
                    continue
                    
                if not full_content:
                    console.print("[gray50](Model did not generate a response)[/]")
                
                # Fable 5 Auto-Correction Phase
                if modified_files and not self._fable_tested:
                    self._fable_tested = True
                    from .ui import MUTED_COLOR
                    console.print("\n[magenta bold]● auto testing app[/magenta bold]")
                    import subprocess
                    test_results = ""
                    for f in list(modified_files):
                        if not os.path.exists(f): continue
                        console.print(f"[{MUTED_COLOR}]  |_ Testing {f}...[/]")
                        try:
                            cmd = ["node", f] if f.endswith(".js") else ["python", f]
                            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                            if res.returncode != 0:
                                test_results += f"File {f} failed with exit code {res.returncode}:\n{res.stderr or res.stdout}\n\n"
                        except Exception as e:
                            test_results += f"Could not run {f}: {e}\n\n"
                            
                    if test_results:
                        console.print("[red bold]✗ Tests failed! Model will autonomously fix the code.[/red bold]")
                        self.context.add_assistant_message(full_content)
                        self.context.add_user_message(f"System Error (Fable 5 Auto-Test): I automatically tested the files you modified. Some of them crashed. You MUST fix these errors before finishing:\n\n{test_results}\n\nAnalyze the error, plan a fix, and use tools to correct it.")
                        continue
                    else:
                        console.print("[green bold]✓ All edited files executed successfully![/green bold]")

                self.context.add_assistant_message(full_content)
                break
                
            self.context.add_assistant_message(full_content, tool_calls=tool_calls)
            total_tools += len(tool_calls)
            
            # Infinite loop protection
            sig = json.dumps([{"name": tc["function"]["name"], "args": tc["function"].get("arguments", "{}")} for tc in tool_calls])
            if getattr(self, "last_tool_sig", None) == sig:
                self.consecutive_identical_calls = getattr(self, "consecutive_identical_calls", 0) + 1
            else:
                self.consecutive_identical_calls = 0
                self.last_tool_sig = sig
                
            if self.consecutive_identical_calls == 2:
                console.print("\n[red]⚠️ Loop detected (model repeated the same faulty tool 3 times). Forcing change of approach...[/red]")
                self.context.add_user_message("System Error: You are stuck in a loop. You repeated the EXACT SAME TOOL CALL 3 times and it failed. DO NOT USE THIS EXACT TOOL CALL AGAIN. You must change your approach, use a different tool, or fix the arguments.")
                continue
            elif self.consecutive_identical_calls >= 4:
                console.print("\n[red]⚠️ Auto-execution stopped: Fatal loop detected.[/red]")
                self.context.add_user_message("System: Fatal loop detected. Execution paused.")
                break
                
            # Handle tool calls
            for tc in tool_calls:
                func = tc["function"]
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                
                if not name:
                    console.print("\n[red]⚠️ Przerwane wywołanie narzędzia (ucięte przez limit tokenów).[/red]")
                    self.context.add_tool_message(tc.get("id", "unknown"), "unknown", "System Error: Your tool call was incomplete because you hit the max_tokens limit. Keep your thinking block much shorter and try again.")
                    continue
                    
                if isinstance(args_str, dict):
                    args = args_str
                    args_str = json.dumps(args)
                else:
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {}
                        
                display_name = name.capitalize()
                if name.endswith("_file"):
                    display_name = name.split("_")[0].capitalize()
                
                arg_summary = ""
                if "path" in args:
                    p = args["path"].replace("\\", "/")
                    parts = p.split("/")
                    if len(parts) > 3:
                        arg_summary = ".../" + "/".join(parts[-3:])
                    else:
                        arg_summary = p
                elif "command" in args:
                    arg_summary = args["command"]
                elif "pattern" in args:
                    arg_summary = f'"{args["pattern"]}"'
                    
                spinner = None
                if name in ["grep", "search_web"]:
                    from .ui import SearchSpinner
                    spinner = SearchSpinner(args.get("query", args.get("pattern", "")), is_web=(name == "search_web"))
                    spinner.start()
                else:
                    print_tool_call(display_name, arg_summary)
                
                # Check for confirmations based on mode
                is_md_in_plan = mode == "plan" and name in ["write_file", "create_file", "edit_file"] and args.get("path", "").endswith(".md")
                
                if mode == "plan" and name in ["write_file", "edit_file", "delete_file", "bash", "create_file", "run_python"] and not is_md_in_plan:
                    result = "Error: Tool execution blocked in 'plan' mode. You can only create/edit .md files (e.g. plan.md)."
                    if spinner:
                        spinner.stop("Error")
                    else:
                        print_tool_result(result)
                else:
                    is_modifying = name in ["write_file", "edit_file", "delete_file", "create_file", "bash", "run_python"]
                    is_dangerous = name in ["bash", "run_python"]
                    
                    if name in ["write_file", "edit_file", "create_file"]:
                        p = args.get("path", "")
                        if p.endswith(".py") or p.endswith(".js"):
                            modified_files.add(os.path.abspath(p))

                    if name in ["write_file", "create_file"]:
                        print_code_panel(os.path.abspath(args.get("path", "file")), args.get("content", ""))
                    elif name == "edit_file":
                        print_diff(args.get("path", "file"), args.get("old_str", ""), args.get("new_str", ""))
                    elif name == "bash":
                        cmd_str = args.get("command", "").strip()
                        if not cmd_str:
                            # Próba "samoleczenia" - jeśli model nazwał argument "cmd" lub "script" zamiast "command"
                            for k, v in args.items():
                                if isinstance(v, str) and v.strip():
                                    cmd_str = v.strip()
                                    args["command"] = cmd_str
                                    break
                                    
                        if not cmd_str:
                            err_msg = "System Error: You returned an empty command. You must provide the command in the 'command' argument."
                            print_tool_result("Empty command - auto-rejected")
                            self.context.add_tool_message(tc["id"], name, err_msg)
                            continue
                        print_code_panel("Terminal", cmd_str, lexer_override="bash")
                    elif name == "run_python":
                        if "code" in args:
                            print_code_panel("Python Run (Code)", args["code"], lexer_override="python")
                        else:
                            try:
                                with open(args.get("path", ""), "r", encoding="utf-8") as f:
                                    file_content = f.read()
                                print_code_panel(f"Python Run ({args.get('path')})", file_content, lexer_override="python")
                            except:
                                print_code_panel("Python Run", f"python {args.get('path', 'script.py')}", lexer_override="bash")
                        
                    requires_prompt = False
                    if mode != "auto" and not is_md_in_plan and is_modifying:
                        requires_prompt = True
                    # W trybie auto wszystkie komendy, nawet bash, lecą z automatu:
                    # elif mode == "auto" and not is_md_in_plan and is_dangerous:
                    #     requires_prompt = True
                        
                    ans = "y"
                    if requires_prompt:
                        import questionary
                        try:
                            choice = questionary.select(
                                "Action requires approval:",
                                choices=[
                                    questionary.Choice("Approve (y)", value="y"),
                                    questionary.Choice("Reject (n)", value="n"),
                                    questionary.Choice("Always allow (a)", value="a")
                                ]
                            ).ask()
                        except Exception:
                            choice = input("Accept? (y)es (n)o (a)lways: ").strip().lower()
                        ans = choice if choice else "n"
                        
                        if ans == "a":
                            mode = "auto"
                            try:
                                input_handler.mode_index = input_handler.modes.index("auto")
                            except:
                                pass
                                
                    if ans == "n":
                        reason = input("  ❯ Enter reason for rejection (optional): ").strip()
                        if reason:
                            result = f"User rejected the operation. Reason: {reason}\nPlease rethink and try a different approach."
                        else:
                            result = "User rejected the operation. Please rethink and try a different approach."
                        if spinner: spinner.stop("Rejected")
                        else: print_tool_result("Rejected. Model will try again.")
                    else:
                        result = execute_tool(name, args, restricted_dir=os.getcwd() if getattr(self.context, 'ide_mode', False) else None)
                        
                        if spinner:
                            lines = len([l for l in str(result).splitlines() if l.strip() and "Results for" not in l])
                            summary = f"{lines} results" if "Error" not in str(result) else "Error"
                            spinner.stop(summary, details=str(result))
                        elif name in ["read_file"]:
                            lines = len(str(result).splitlines())
                            print_tool_result(f"Read {lines} lines")
                        elif name == "edit_file":
                            added = len(args.get("new_str", "").splitlines())
                            removed = len(args.get("old_str", "").splitlines())
                            print_tool_result(f"Edited {args.get('path', 'file')} ([green]+{added}[/] / [red]-{removed}[/])")
                        elif name in ["write_file", "create_file"]:
                            added = len(args.get("content", "").splitlines())
                            print_tool_result(f"Created/Overwritten {args.get('path', 'file')} ({added} lines)")
                        elif name == "bash":
                            if "Exit code: 0" in str(result):
                                print_tool_result("Command successful")
                            else:
                                print_tool_result("Command failed")
                        else:
                            res_str = str(result)
                            print_tool_result(res_str[:60].replace("\n", " ") + "..." if len(res_str) > 60 else res_str.replace("\n", " "))

                self.context.add_tool_message(tc["id"], name, str(result))
                
        elapsed = time.time() - turn_start
        tokens = getattr(self.context, 'count_tokens', lambda: 0)()
        print_turn_done(elapsed, tokens, total_tools)
