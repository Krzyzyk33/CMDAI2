import os
import glob
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

def create_picker_app(tabs, options_dict, start_tab=0):
    current_tab = start_tab
    selected_index = {i: 0 for i in range(len(tabs))}
    result = {"action": None, "tab": None, "value": None}
    
    bindings = KeyBindings()
    
    @bindings.add("q")
    @bindings.add("c-c")
    def _(event):
        result["action"] = "cancel"
        event.app.exit()
        
    @bindings.add("left")
    def _(event):
        nonlocal current_tab
        current_tab = (current_tab - 1) % len(tabs)
        
    @bindings.add("right")
    def _(event):
        nonlocal current_tab
        current_tab = (current_tab + 1) % len(tabs)
        
    @bindings.add("up")
    def _(event):
        idx = selected_index[current_tab]
        opts = options_dict[current_tab]
        selected_index[current_tab] = (idx - 1) % len(opts)
        
    @bindings.add("down")
    def _(event):
        idx = selected_index[current_tab]
        opts = options_dict[current_tab]
        selected_index[current_tab] = (idx + 1) % len(opts)
        
    @bindings.add("enter")
    def _(event):
        result["tab"] = tabs
        result["action"] = "select"
        event.app.exit()
        
    def get_text():
        lines = []
        lines.append(("", "\n"))
        
        # Tabs row
        for i, t in enumerate(tabs):
            if i == current_tab:
                lines.append(("class:active_tab", f"  > {t}  "))
            else:
                lines.append(("class:inactive_tab", f"    {t}  "))
        lines.append(("", "\n\n"))
        
        # Options
        opts = options_dict[current_tab]
        for i, opt in enumerate(opts):
            if i == selected_index[current_tab]:
                lines.append(("class:selected", f" > {opt}\n"))
            else:
                lines.append(("class:unselected", f"   {opt}\n"))
                
        lines.append(("class:help", "\n(Strzałki: nawigacja, Enter: wybór, q: wyjście)\n"))
        return lines

    style = Style.from_dict({
        "active_tab": "fg:#00ffff bold",
        "inactive_tab": "fg:#aaaaaa",
        "selected": "fg:#00ffff bold",
        "unselected": "fg:#aaaaaa",
        "help": "fg:#666666 italic"
    })
    
    control = FormattedTextControl(get_text)
    window = Window(content=control)
    layout = Layout(HSplit([window]))
    
    app = Application(
        layout=layout,
        key_bindings=bindings,
        style=style,
        full_screen=False
    )
    
    app.run()
    return result

def run_model_picker(state):
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(app_dir, "models")
    local_models = glob.glob(os.path.join(models_dir, "*.gguf"))
    local_models = [os.path.basename(m) for m in local_models]
    
    api_models = state.get("api_models", [])
    
    tabs = ["Ustawienia", "Lokalne modele", "Modele API"]
    options = {
        0: ["Dodaj model", "Dodaj klucz API", "Edytuj modele", "Wyjdź"],
        1: local_models if local_models else ["Brak modeli lokalnych"],
        2: [m["name"] for m in api_models] if api_models else ["Brak modeli API"]
    }
    
    res = create_picker_app(tabs, options, start_tab=1)
    
    out = {"action": "cancel", "value": None}
    if res["action"] == "select":
        tab = res["tab"]
        val = res["value"]
        if tab == "Ustawienia":
            if val == "Dodaj model":
                out["action"] = "add_model"
            elif val == "Dodaj klucz API":
                out["action"] = "add_api"
        elif tab == "Lokalne modele":
            if val != "Brak modeli lokalnych":
                out["action"] = "load_local"
                out["value"] = os.path.join(models_dir, val)
        elif tab == "Modele API":
            if val != "Brak modeli API":
                out["action"] = "load_api"
                for m in api_models:
                    if m["name"] == val:
                        out["value"] = m
                        break
    return out

def run_provider_picker(mode="api"):
    tabs = ["Nvidia NIM", "OpenAI"]
    if mode == "api":
        options = {
            0: ["Wpisz klucz API", "Anuluj"],
            1: ["Wpisz klucz API", "Anuluj"]
        }
    else:
        options = {
            0: ["Wpisz nazwę modelu", "Anuluj"],
            1: ["Wpisz nazwę modelu", "Anuluj"]
        }
        
    res = create_picker_app(tabs, options, start_tab=0)
    out = {"action": "cancel", "provider": None}
    
    if res["action"] == "select" and res["value"] != "Anuluj":
        out["action"] = "continue"
        if res["tab"] == "Nvidia NIM":
            out["provider"] = "nvidia"
        elif res["tab"] == "OpenAI":
            out["provider"] = "openai"
            
    return out
