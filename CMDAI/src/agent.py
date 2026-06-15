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
        
    def get_tool_desc(self) -> str:
        desc = ""
        for t in TOOLS_DEFINITIONS:
            f = t["function"]
            desc += f"- {f['name']}: {f['description']}\n"
        return desc
        
    def handle_user_input(self, user_msg: str, mode: str, input_handler):
        import time
        from .ui import print_turn_done
        
        self.context.add_user_message(user_msg)
        
        turn_start = time.time()
        total_tools = 0
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            tree = ThinkingTree(expanded=input_handler.thinking_expanded)
            tree.start()
            
            level_info = input_handler.thinking_levels[input_handler.thinking_idx]
            level_idx = input_handler.thinking_idx
            
            if level_idx == 0:
                thinking_desc = "You MUST wrap your thoughts inside <think> and </think> tags.\nTHINKING BEHAVIOR - LOW:\nNie generuj sekcji THINK. Przejdź od razu do ACTION lub odpowiedzi tekstowej.\nWyjątek: jeśli zadanie wymaga wyboru pliku/funkcji do edycji i nie jest to oczywiste z promptu użytkownika, napisz tylko:\n<think>\nROZUMIEM: <czego dotyczy zadanie>\nPLAN: <1 linia>\n</think>\n\nPo wykonaniu akcji NIE generuj THINK, niezależnie od wyniku.\nWyjątek: jeśli Bash zwrócił błąd, napisz 1 linię diagnozy w <think> i natychmiast zaproponuj poprawkę w kolejnym ACTION.\nNie wykonuj dodatkowych akcji 'na zapas' (build, search) jeśli użytkownik o to nie prosił."
            elif level_idx == 1:
                thinking_desc = "You MUST wrap your thoughts inside <think> and </think> tags.\nTHINKING BEHAVIOR - MEDIUM:\nNa początku tury wygeneruj zwięzły THINK dokładnie wewnątrz tagów <think> i </think>:\n<think>\nROZUMIEM: <czego dotyczy zadanie>\nPLAN: <krótka lista kroków (max 3)>\n</think>\n\nNie generuj sub-drzew.\nPo wykonaniu akcji odczytu (Read/Search) NIE generuj THINK, chyba że wynik drastycznie różni się od oczekiwań.\nPo akcjach modyfikujących (Edit/Write/Bash) możesz wygenerować krótki THINK (1-2 linie), jeśli wymaga tego aktualizacja planu.\n\nWymuszone akcje: Wyszukaj wszystkich callerów po zmianie sygnatury funkcji (ACTION: Search). Nie wykonuj budowania projektu (build), dopóki użytkownik o to nie poprosi."
            elif level_idx == 2:
                thinking_desc = "You MUST wrap your thoughts inside <think> and </think> tags.\nTHINKING BEHAVIOR - HIGH:\nNa początku tury wygeneruj ustrukturyzowany THINK dokładnie wewnątrz tagów <think> i </think>:\n<think>\nROZUMIEM: <czego dotyczy zadanie>\nOPCJE: <opcja A> | <opcja B> (tylko dla złożonych lub niejednoznacznych problemów)\nWYBOR: <wybrana opcja + krótkie uzasadnienie>\nPLAN: <ponumerowana lista kroków>\n</think>\n\nStosuj sub-drzewa (wcięte listy) tylko w przypadku istotnych decyzji architektonicznych.\nPo kluczowych akcjach wygeneruj krótki THINK potwierdzający status:\n<think>\nPOTWIERDZENIE: <status + następny krok>\n</think>\n\nWymuszone akcje: ZAWSZE wyszukaj callerów po zmianie sygnatury funkcji. Po zakończeniu bloku powiązanych ze sobą edycji kodu - ZAWSZE uruchom build."
            elif level_idx == 3:
                thinking_desc = "You MUST wrap your thoughts inside <think> and </think> tags.\nTHINKING BEHAVIOR - ULTRA:\nNa początku KAŻDEJ tury wygeneruj THINK dokładnie wewnątrz tagów <think> i </think>:\n<think>\nROZUMIEM: <czego dotyczy zadanie>\nKONTEKST: <co już wiesz z dotychczasowych akcji>\nOPCJE: <opcja A> | <opcja B>\nWYBOR: <wybrana opcja + uzasadnienie>\nRYZYKO: <potencjalny problem + mitygacja>\nPLAN: <ponumerowana lista kroków>\n\nDla KAŻDEGO punktu PLAN, który ma więcej niż jeden sposób wykonania, rozpisz sub-drzewo:\n  - <punkt planu>\n    > opcja 1\n    > opcja 2\n    > wybór + uzasadnienie\n</think>\n\nPo KAŻDEJ akcji wygeneruj nowy THINK:\n<think>\nPOTWIERDZENIE: <czy wynik zgodny z oczekiwaniem? co dalej?>\n</think>\n\nWymuszone akcje: ZAWSZE wyszukaj callerów po zmianie sygnatury. ZAWSZE uruchom build po edycji kodu."
            elif level_idx == 4:
                thinking_desc = "You MUST wrap your thoughts inside <think> and </think> tags.\nTHINKING BEHAVIOR - EXTREME:\nNa początku KAŻDEJ tury przeanalizuj cały projekt. Wygeneruj wyczerpujący THINK dokładnie wewnątrz tagów <think> i </think>:\n<think>\nROZUMIEM: <czego dotyczy zadanie w skali całego projektu>\nKONTEKST: <wnioski z logów, struktury plików i architektury>\nOPCJE: <rozbudowana lista opcji i ścieżek>\nWYBOR: <ostateczny wybór + wpływ na inne moduły>\nRYZYKO: <szczegółowa lista przypadków brzegowych, security i performance>\nPLAN: <bardzo szczegółowa lista kroków>\n\nDla KAŻDEGO punktu PLAN musisz rozpisać wielopoziomowe sub-drzewo. W pierwszej iteracji MUSISZ użyć narzędzia 'submit_plan'.\n</think>\n\nPo KAŻDEJ akcji wykonaj głęboką ewaluację:\n<think>\nEWALUACJA: <szczegółowa analiza zwróconego wyniku, diagnoza błędów, poprawki do planu>\n</think>\n\nWymuszone akcje: ZAWSZE wyszukaj wszystkie zależności. ZAWSZE uruchom build i testy jednostkowe po KAŻDEJ edycji pliku. Na końcu wykonaj procedurę re-walidacji."

            messages = self.context.get_messages(self.get_tool_desc(), thinking_desc=thinking_desc)
            
            # Filtrowanie narzędzi
            if mode == "plan":
                allowed_tools = ["read_file", "list_dir", "grep", "search_web", "save_plan"]
                filtered_tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in allowed_tools]
            else:
                disallowed_tools = ["save_plan"]
                if level_idx == 4 and iteration == 1:
                    allowed = ["read_file", "list_dir", "grep", "search_web", "submit_plan"]
                    filtered_tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] in allowed]
                else:
                    disallowed_tools.append("submit_plan")
                    filtered_tools = [t for t in TOOLS_DEFINITIONS if t["function"]["name"] not in disallowed_tools]
            
            use_native_tools = (level_idx == 0)
            if not use_native_tools:
                messages[0]["content"] += "\n\nCRITICAL: You are configured to use TEXT-BASED TOOL CALLING. You MUST NOT use native function calling. Output your tool call as a JSON markdown block after your <think> block."
                passed_tools = None
            else:
                passed_tools = filtered_tools
                
            stream = self.model.stream_chat(messages, tools=passed_tools, reasoning_budget=level_info[1])
            
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
            
            try:
                for content, thinking, tc in stream:
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
                    console.print("\n[yellow]⚠ Model wygenerował całkowicie pustą odpowiedź. Ponawiam próbę (self-correction)...[/yellow]")
                    self.context.add_user_message("System Error: Zwróciłeś pustą odpowiedź. Pamiętaj o wygenerowaniu bloku <think> (jeśli wymagany) i podjęciu akcji lub udzieleniu odpowiedzi tekstowej.")
                else:
                    console.print("\n[yellow]⚠ Model wygenerował tylko myślenie, ale nie podjął akcji. Ponawiam próbę (self-correction)...[/yellow]")
                    self.context.add_user_message("System Error: Wygenerowałeś blok <think>, ale nie użyłeś narzędzia ani nie napisałeś żadnej widocznej odpowiedzi poza myśleniem. Użyj narzędzia lub powiedz coś.")
                continue

            if level_idx > 0 and not full_thinking.strip() and not ("<think>" in full_content):
                console.print("\n[yellow]⚠ Model zignorował obowiązek myślenia. Ponawiam próbę (self-correction)...[/yellow]")
                self.context.add_assistant_message(full_content)
                self.context.add_user_message("System Error: Złamałeś zasady. Musisz wygenerować blok <think>...</think> z analizą przed użyciem narzędzia lub przesłaniem odpowiedzi. Spróbuj ponownie.")
                continue

            tree.print_tree()

            if not tool_calls:
                if not full_content:
                    console.print("[gray50](Model nie wygenerował odpowiedzi)[/]")
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
                
            if self.consecutive_identical_calls >= 2:
                console.print("\n[red]⚠ Zatrzymano automatyczne wywołania: Wykryto pętlę (model 3 razy powtórzył to samo, błędne narzędzie).[/red]")
                self.context.add_user_message("System: Przestań używać tego narzędzia, utknąłeś w pętli. Przeanalizuj błąd i powiedz mi, co nie działa, lub poproś o wskazówki.")
                break
                
            # Handle tool calls
            for tc in tool_calls:
                func = tc["function"]
                name = func["name"]
                args_str = func.get("arguments", "{}")
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
                    
                    if name in ["write_file", "create_file"]:
                        print_code_panel(os.path.abspath(args.get("path", "file")), args.get("content", ""))
                    elif name == "edit_file":
                        print_diff(args.get("path", "file"), args.get("old_str", ""), args.get("new_str", ""))
                    elif name == "bash":
                        print_code_panel("Terminal", args.get("command", ""), lexer_override="bash")
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
                    elif mode == "auto" and not is_md_in_plan and is_dangerous:
                        requires_prompt = True
                        
                    ans = "y"
                    if requires_prompt:
                        import questionary
                        try:
                            choice = questionary.select(
                                "Akcja wymaga zatwierdzenia:",
                                choices=[
                                    questionary.Choice("Zatwierdź (y)", value="y"),
                                    questionary.Choice("Odrzuć (n)", value="n"),
                                    questionary.Choice("Zawsze zezwalaj (a)", value="a")
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
                        reason = input("  ⎿  Podaj powód odrzucenia (opcjonalnie): ").strip()
                        if reason:
                            result = f"User rejected the operation. Reason: {reason}\nPlease rethink and try a different approach."
                        else:
                            result = "User rejected the operation. Please rethink and try a different approach."
                        if spinner: spinner.stop("Rejected")
                        else: print_tool_result("Odrzucono. Model spróbuje ponownie.")
                    else:
                        result = execute_tool(name, args, restricted_dir=os.getcwd() if getattr(self.context, 'ide_mode', False) else None)
                        
                        if spinner:
                            lines = len([l for l in result.splitlines() if l.strip() and "Results for" not in l])
                            summary = f"{lines} results" if "Error" not in result else "Error"
                            spinner.stop(summary, details=result)
                        elif name in ["read_file"]:
                            lines = len(result.splitlines())
                            print_tool_result(f"Read {lines} lines")
                        elif name == "edit_file":
                            added = len(args.get("new_str", "").splitlines())
                            removed = len(args.get("old_str", "").splitlines())
                            print_tool_result(f"Zmieniono {args.get('path', 'file')} ([green]+{added}[/] / [red]-{removed}[/])")
                        elif name in ["write_file", "create_file"]:
                            added = len(args.get("content", "").splitlines())
                            print_tool_result(f"Utworzono/Nadpisano {args.get('path', 'file')} ({added} linii)")
                        elif name == "bash":
                            if "Exit code: 0" in result:
                                print_tool_result("Command successful")
                            else:
                                print_tool_result("Command failed")
                        else:
                            print_tool_result(result[:60].replace("\n", " ") + "..." if len(result) > 60 else result.replace("\n", " "))

                
                self.context.add_tool_message(tc["id"], name, result)
                
        elapsed = time.time() - turn_start
        tokens = self.context.count_tokens()
        print_turn_done(elapsed, tokens, total_tools)
