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
                sm = context.session_manager
                sessions = sm.get_all_sessions()
                console.print("\n[bold]Dostępne sesje:[/bold]")
                for i, s in enumerate(sessions):
                    mark = "[green]*[/]" if s == sm.current_state.session_id else " "
                    console.print(f"  {mark} [{i+1}] {s}")
                
                sel = input("\nWybierz numer sesji (lub 'n' by stworzyć nową, enter by anulować): ").strip()
                if sel.lower() == 'n':
                    new_id = input("Podaj nazwę nowej sesji: ").strip()
                    if new_id:
                        sm.load_state(new_id)
                        context.messages = []
                        console.print(f"[green]Utworzono i przełączono na sesję: {new_id}[/green]")
                elif sel.isdigit() and 1 <= int(sel) <= len(sessions):
                    s_id = sessions[int(sel)-1]
                    sm.load_state(s_id)
                    context.messages = []
                    console.print(f"[green]Przełączono na sesję: {s_id}[/green]")
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
                    api_key = input(f"\n[bold]Podaj klucz API dla {provider.upper()}: [/bold]")
                    if api_key:
                        if "api_keys" not in state:
                            state["api_keys"] = {}
                        state["api_keys"][provider] = api_key
                        save_state(state)
                        console.print(f"[green]Zapisano klucz API dla {provider.upper()}.[/green]")
                        import time; time.sleep(1)
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
                        console.print(f"\n[red]Brak klucza API dla {provider.upper()}! Najpierw wybierz 'Dodaj klucz API'.[/red]")
                        import time; time.sleep(2)
                        os.system("cls" if os.name == "nt" else "clear")
                        print_header(os.path.basename(model_path), cwd)
                        continue
                        
                    model_name = input(f"\n[bold]Podaj nazwę modelu dla {provider.upper()}: [/bold]")
                    if model_name:
                        base_url = "https://integrate.api.nvidia.com/v1" if provider == "nvidia" else "https://api.openai.com/v1"
                        if provider == "nvidia":
                            base_url = "https://integrate.api.nvidia.com/v1"
                        elif provider == "groq":
                            base_url = "https://api.groq.com/openai/v1"
                        else:
                            base_url = "https://api.openai.com/v1"
                        new_api_model = {"name": model_name, "api_key": api_keys[provider], "base_url": base_url}
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
                    console.print(f"\n[green]Przełączono na {os.path.basename(new_model_path)}. ⏳ Trwa ładowanie modelu do VRAM...[/green]")
                    
                    del agent.model
                    del model
                    import gc
                    gc.collect()
                    
                    model_path = new_model_path
                    model = LlamaModel(model_path)
                    agent.model = model
                    os.system("cls" if os.name == "nt" else "clear")
                    print_header(os.path.basename(model_path), cwd)
                    
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
                continue
            else:
                console.print(f"Unknown command or not implemented: {user_input}")
            continue
            
        # Add IDE context to user prompt if any
        ide_ctx = ide_server.get_ide_context()
        if ide_ctx:
            user_input += f"\n\n[IDE Context]\n{ide_ctx}"
            
        print_user_msg(user_input)
        agent.handle_user_input(user_input, mode, input_handler)
        
        # Auto-compaction if context exceeds 50%
        limit = model.get_context_limit()
        if context.count_tokens() >= limit * 0.5:
            context.trigger_compaction(model)
if __name__ == "__main__":
    main()
