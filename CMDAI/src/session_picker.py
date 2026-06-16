import os
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

def run_session_picker(sessions, current_session_id):
    """
    sessions to lista słowników: [{"id": "xyz", "date": "2026-06-16 12:00"}, ...]
    """
    options = ["[Nowa sesja]"]
    for s in sessions:
        options.append(s)
    options.append("[Anuluj]")
    
    selected_index = 0
    # Stan usuwania: jeśli delete_mode to True, użytkownik wcisnął strzałkę w prawo
    delete_mode = False
    
    result = {"action": "cancel", "value": None}
    
    bindings = KeyBindings()
    
    @bindings.add("q")
    @bindings.add("c-c")
    def _(event):
        result["action"] = "cancel"
        event.app.exit()
        
    @bindings.add("up")
    def _(event):
        nonlocal selected_index, delete_mode
        selected_index = (selected_index - 1) % len(options)
        delete_mode = False
        
    @bindings.add("down")
    def _(event):
        nonlocal selected_index, delete_mode
        selected_index = (selected_index + 1) % len(options)
        delete_mode = False
        
    @bindings.add("right")
    def _(event):
        nonlocal delete_mode
        opt = options[selected_index]
        if isinstance(opt, dict): # Tylko prawdziwe sesje można usunąć
            delete_mode = True
            
    @bindings.add("left")
    def _(event):
        nonlocal delete_mode
        delete_mode = False
        
    @bindings.add("enter")
    def _(event):
        opt = options[selected_index]
        if isinstance(opt, str):
            if opt == "[Nowa sesja]":
                result["action"] = "new"
            else:
                result["action"] = "cancel"
        else:
            if delete_mode:
                result["action"] = "delete"
                result["value"] = opt["id"]
            else:
                result["action"] = "load"
                result["value"] = opt["id"]
        event.app.exit()
        
    def get_formatted_text():
        text = [
            ("class:title", "Wybierz sesję (Strzałki: góra/dół. Prawa strzałka = usuń):\n"),
            ("", "―" * 50 + "\n")
        ]
        
        for i, opt in enumerate(options):
            is_selected = (i == selected_index)
            prefix = "> " if is_selected else "  "
            
            if isinstance(opt, str):
                line = f"{prefix}{opt}"
                style = "class:selected" if is_selected else ""
                text.append((style, line + "\n"))
            else:
                s_id = opt["id"]
                s_date = opt["date"]
                active_mark = "* " if s_id == current_session_id else "  "
                
                if is_selected and delete_mode:
                    line = f"{prefix}{active_mark}{s_id} ({s_date})   [Wciśnij ENTER, aby potwierdzić USUNIĘCIE]"
                    style = "class:delete_mode"
                else:
                    delete_hint = "   [-> Usuń]" if is_selected else ""
                    line = f"{prefix}{active_mark}{s_id} ({s_date}){delete_hint}"
                    style = "class:selected" if is_selected else ("class:active" if active_mark.strip() else "")
                
                text.append((style, line + "\n"))
                
        text.append(("", "―" * 50 + "\n"))
        text.append(("", " ENTER - wybierz/zatwierdź | Q - wyjście"))
        return text

    layout = Layout(
        HSplit([
            Window(content=FormattedTextControl(get_formatted_text))
        ])
    )
    
    style = Style([
        ("title", "bold #00ff00"),
        ("selected", "bg:#333333 #ffffff"),
        ("active", "#00ffff"),
        ("delete_mode", "bg:#ff0000 #ffffff bold"),
    ])
    
    app = Application(
        layout=layout,
        key_bindings=bindings,
        style=style,
        full_screen=False
    )
    app.run()
    return result
