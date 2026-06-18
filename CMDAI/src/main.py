import os
import glob
import json
from .llama import LlamaModel
from .context import ContextManager
from .agent import Agent
from .ui import print_header, print_user_msg, console
from .input import InputHandler
from .ide import IDEServer
STATE_FILE = os.path.expanduser("~/.cmdai2/state.json")
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}
def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
def get_default_model():
    state = load_state()
    model_type = state.get("model_type", "local")
    
    if model_type == "api":
        active_model = state.get("active_api_model")
        if active_model:
            return "api", active_model
            
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(app_dir, "models")
    models = glob.glob(os.path.join(models_dir, "*.gguf"))
    if not models:
        console.print("[red]No .gguf models found in models/ directory.[/red]")
        exit(1)
        
    saved_model = state.get("model_path")
    if saved_model and saved_model in models:
        return "local", saved_model
    return "local", models[-1]
def print_chat_history(context):
    import re
    from rich.markdown import Markdown
    from .ui import console, ACCENT_COLOR, print_tool_call, print_tool_result, print_user_msg, print_code_panel, print_diff
    import os
    
    for msg in context.messages:
        if msg['role'] == 'user':
            content = msg.get('content', '')
            if content.startswith('<tool_response>'):
                res_str = content.replace('<tool_response>\n', '').replace('\n</tool_response>', '').strip()
                print_tool_result(res_str[:60].replace("\n", " ") + "..." if len(res_str) > 60 else res_str.replace("\n", " "))
            else:
                print_user_msg(content)
        elif msg['role'] == 'assistant':
            text = msg.get('content', '')
            text = re.sub(r'<think>.*?(?:</think>|$)', '*(Thinking hidden...)*', text, flags=re.DOTALL|re.IGNORECASE)
            text = re.sub(r'```(?:json)?\s*\{.*?"name"\s*:.*?\}\s*```', '', text, flags=re.DOTALL)
            text = re.sub(r'\{\s*"name"\s*:.*?"arguments"\s*:.*?\}', '', text, flags=re.DOTALL)
            text = text.strip()
            if text:
                console.print(f"\n")
                console.print(Markdown(text))
            
            if 'tool_calls' in msg and msg['tool_calls']:
                for tc in msg['tool_calls']:
                    func = tc.get('function', {})
                    name = func.get('name', 'unknown')
                    args = func.get('arguments', {})
                    if isinstance(args, str):
                        import json
                        try:
                            args = json.loads(args)
                        except:
                            args = {}
                            
                    display_name = name.capitalize()
                    if name.endswith("_file"):
                        display_name = name.split("_")[0].capitalize()
                        
                    arg_summary = ""
                    if "path" in args:
                        p = args["path"].replace("\\", "/")
                        parts = p.split("/")
                        arg_summary = ".../" + "/".join(parts[-3:]) if len(parts) > 3 else p
                        if name == "read_file":
                            offset = args.get("offset", 0)
                            limit = args.get("limit", 0)
                            if offset > 0 or limit > 0:
                                end_str = f"{offset + limit}" if limit > 0 else "koniec"
                                arg_summary += f" (linie {offset}-{end_str})"
                    elif "command" in args:
                        arg_summary = args["command"]
                    elif "pattern" in args:
                        arg_summary = f'"{args["pattern"]}"'
                        
                    print_tool_call(display_name, arg_summary)
                    
                    if name in ["write_file", "create_file"]:
                        print_code_panel(os.path.abspath(args.get("path", "file")), args.get("content", ""))
                    elif name == "edit_file":
                        print_diff(args.get("path", "file"), args.get("old_str", ""), args.get("new_str", ""))
                    elif name == "bash":
                        print_code_panel("Terminal", args.get("command", ""), lexer_override="bash")
                    elif name == "run_python":
                        if "code" in args:
                            print_code_panel("Python Run (inline)", args.get("code", ""), lexer_override="python")
                        else:
                            print_code_panel("Python Run", f"python {args.get('path', 'script.py')}", lexer_override="bash")

def main():
    console.clear()
    m_type, m_val = get_default_model()
    
    # Initialize components
    if m_type == "api":
        from .api_model import OpenAIAPIModel
        model_path = m_val['name']
        model = OpenAIAPIModel(model_name=m_val['name'], api_key=m_val['api_key'], base_url=m_val['base_url'])
    else:
        model_path = m_val
        model = LlamaModel(model_path)
    context = ContextManager()
    agent = Agent(model, context)
    
    saved_state = load_state()
    input_handler = InputHandler(thinking_idx=saved_state.get("thinking_idx", 1))
    
    ide_server = IDEServer()
    ide_server.start()
    
    cwd = os.getcwd()
    
    os.system("cls" if os.name == "nt" else "clear")
    mode = input_handler.get_mode()
    print_header(os.path.basename(model_path), cwd)
    
    import shutil
    import shutil
    
    # We now handle the layout spacing inside prompt_toolkit itself
    # so that the completion menu knows how much vertical space it has.
        
    while True:
        tokens = context.count_tokens()
        user_input = input_handler.get_input(os.path.basename(model_path), tokens, model.get_context_limit())
        mode = input_handler.get_mode()
        
        current_state = load_state()
        if current_state.get("thinking_idx") != input_handler.thinking_idx:
            current_state["thinking_idx"] = input_handler.thinking_idx
            save_state(current_state)
            
        if not user_input:
            continue
            
        if user_input.startswith("/"):
            if user_input == "/quit":
                break
            elif user_input == "/clear":
                context.clear()
                console.clear()
            elif user_input == "/compact":
                context.trigger_compaction(model)
            elif user_input.startswith("/sessions"):
                while True:
                    sm = context.session_manager
                    sessions = sm.get_all_sessions()
                    
                    from .session_picker import run_session_picker
                    res = run_session_picker(sessions, sm.current_state.session_id)
                    
                    if res["action"] == "cancel":
                        console.clear()
                        print_header(os.path.basename(model_path), cwd)
                        print_chat_history(context)
                        break
                        
                    if res["action"] == "new":
                        import questionary
                        new_id = questionary.text("Podaj nazwę nowej sesji (enter by anulować):").ask()
                        if new_id and new_id.strip():
                            new_id = new_id.strip()
                            context.load_history(new_id)
                            console.clear()
                            print_header(os.path.basename(model_path), cwd)
                            console.print(f"[green]Utworzono i przełączono na sesję: {new_id} (wczytano {len(context.messages)} wiadomości)[/green]")
                        else:
                            console.clear()
                            print_header(os.path.basename(model_path), cwd)
                            print_chat_history(context)
                        break
                    elif res["action"] == "delete":
                        del_id = res["value"]
                        sm.delete_session(del_id)
                        console.clear()
                        print_header(os.path.basename(model_path), cwd)
                        console.print(f"[yellow]Successfully deleted session: {del_id}[/yellow]")
                        
                        if del_id == sm.current_state.session_id:
                            context.clear()
                            console.print("[yellow]Deleted active session. Starting a new one.[/yellow]")
                        # brak break -> wraca do wyświetlenia listy
                    elif res["action"] == "load":
                        s_id = res["value"]
                        context.load_history(s_id)
                        console.clear()
                        print_header(os.path.basename(model_path), cwd)
                        console.print(f"[green]Przełączono na sesję: {s_id} (wczytano {len(context.messages)} wiadomości)[/green]")
                        
                        print_chat_history(context)
                        break
                continue
            elif user_input == "/ide":
                in_ide = os.environ.get("TERM_PROGRAM") in ["vscode", "JetBrains-JediTerm"] or "VSCODE_PID" in os.environ or "TERMINAL_EMULATOR" in os.environ
                if not in_ide:
                    console.print("[red]Błąd: Integracja /ide może być włączona tylko gdy aplikacja działa wewnątrz wbudowanego terminala IDE (VS Code, JetBrains itp.).[/red]")
                else:
                    context.ide_mode = True
                    console.print(f"[green]IDE Server running on port {ide_server.port}. Włączono rygorystyczną izolację projektu.[/green]")
            elif user_input == "/auto":
                input_handler.mode_index = input_handler.modes.index("auto")
                console.print("[green]Tryb zmieniony na: auto[/green]")
            elif user_input == "/code":
                input_handler.mode_index = input_handler.modes.index("code")
                console.print("[green]Tryb zmieniony na: code[/green]")
            elif user_input == "/plan":
                input_handler.mode_index = input_handler.modes.index("plan")
                console.print("[green]Tryb zmieniony na: plan[/green]")
            elif user_input == "/model":
                from .model_picker import run_model_picker
                state = load_state()
                result = run_model_picker(state)
                
                if result["action"] == "add_api":
                    from .model_picker import run_provider_picker
                    sub_res = run_provider_picker(mode="api")
                    if sub_res["action"] == "cancel":
                        os.system("cls" if os.name == "nt" else "clear")
                        print_header(os.path.basename(model_path), cwd)
                        continue
                        
                    provider = sub_res["provider"]
                    api_key = console.input(f"\n[bold]Enter API key for {provider.upper()}: [/bold]")
                    if api_key:
                        if "api_keys" not in state:
                            state["api_keys"] = {}
                        state["api_keys"][provider] = api_key
                        save_state(state)
                        console.print(f"[green]Saved API key for {provider.upper()}.[/green]")
                        import time; time.sleep(1)
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    continue
                elif result["action"] == "edit_api":
                    from .manager_ui import run_api_keys_manager
                    run_api_keys_manager(state, save_state)
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    continue
                elif result["action"] == "edit_models":
                    from .manager_ui import run_models_manager
                    run_models_manager(state, save_state)
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    continue
                elif result["action"] == "add_model":
                    from .model_picker import run_provider_picker
                    sub_res = run_provider_picker(mode="model")
                    if sub_res["action"] == "cancel":
                        os.system("cls" if os.name == "nt" else "clear")
                        print_header(os.path.basename(model_path), cwd)
                        continue
                        
                    provider = sub_res["provider"]
                    api_keys = state.get("api_keys", {})
                    if provider not in api_keys:
                        console.print(f"\n[red]Missing API key for {provider.upper()}! Please select 'Add API key' first.[/red]")
                        import time; time.sleep(2)
                        os.system("cls" if os.name == "nt" else "clear")
                        print_header(os.path.basename(model_path), cwd)
                        continue
                        
                    model_name = console.input(f"\n[bold]Podaj nazwę modelu dla {provider.upper()}: [/bold]")
                    if model_name:
                        from src.providers import get_provider
                        provider_module = get_provider(provider)
                        if provider_module:
                            base_url = provider_module.BASE_URL
                        else:
                            base_url = "https://api.openai.com/v1"
                        new_api_model = {"name": model_name, "api_key": api_keys[provider], "base_url": base_url, "provider": provider}
                        if "api_models" not in state:
                            state["api_models"] = []
                        state["api_models"].append(new_api_model)
                        save_state(state)
                        result["action"] = "load_api"
                        result["value"] = new_api_model
                    else:
                        os.system("cls" if os.name == "nt" else "clear")
                        print_header(os.path.basename(model_path), cwd)
                        continue
                        
                if result["action"] == "cancel":
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    continue
                        
                if result["action"] == "load_local":
                    new_model_path = result["value"]
                    state["model_path"] = new_model_path
                    state["model_type"] = "local"
                    save_state(state)
                    console.print(f"\n[green]Switched to {os.path.basename(new_model_path)}. ⏳ Loading model into VRAM...[/green]")
                    
                    del agent.model
                    del model
                    import gc
                    gc.collect()
                    
                    model_path = new_model_path
                    model = LlamaModel(model_path)
                    agent.model = model
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    print_chat_history(context)
                    
                elif result["action"] == "load_api":
                    m_val = result["value"]
                    state["model_type"] = "api"
                    state["active_api_model"] = m_val
                    save_state(state)
                    console.print(f"\n[green]Przełączono na model API: {m_val['name']}[/green]")
                    
                    if hasattr(model, 'llm'):
                        del agent.model
                        del model
                        import gc
                        gc.collect()
                        
                    from .api_model import OpenAIAPIModel
                    model_path = m_val['name']
                    model = OpenAIAPIModel(model_name=m_val['name'], api_key=m_val['api_key'], base_url=m_val['base_url'])
                    agent.model = model
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    print_chat_history(context)
                continue
            else:
                console.print(f"Unknown command or not implemented: {user_input}")
            continue
            
        # Add IDE context to user prompt if any
        ide_ctx = ide_server.get_ide_context()
        if ide_ctx:
            user_input += f"\n\n[IDE Context]\n{ide_ctx}"
            
        if len(context.messages) == 0 and context.session_manager.current_state.session_id == "default":
            import re
            def get_slug(text):
                import unicodedata
                text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()
                text = re.sub(r'[^a-z0-9]+', '_', text)
                return text.strip('_')[:40]
            
            try:
                prompt = f"Wymyśl krótką, opisową nazwę (max 3 słowa) w języku polskim dla zadania: '{user_input[:100]}'. Odpowiedz tylko samą nazwą."
                msgs = [{"role": "user", "content": prompt}]
                t_stream = agent.model.stream_chat(msgs, tools=None)
                title = ""
                for c, _, _ in t_stream:
                    if c: title += c
                slug = get_slug(title)
                if slug:
                    context.rename_session(slug)
                    console.print(f"[dim italic]Auto-nazwa sesji: {slug}[/dim italic]")
            except Exception:
                pass

        print_user_msg(user_input)
        agent.handle_user_input(user_input, mode, input_handler)
        
        # Auto-compaction if context exceeds 50%
        limit = model.get_context_limit()
        if context.count_tokens() >= limit * 0.5:
            context.trigger_compaction(model)
if __name__ == "__main__":
    main()
