import os
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import CompleteStyle
COMMANDS = {
    "/help": "wyświetl szczegółową instrukcję i dostępne skróty klawiszowe",
    "/model": "zmień aktualnie używany model sztucznej inteligencji na inny",
    "/clear": "wyczyść całą historię czatu oraz bufor pamięci z ekranu",
    "/compact": "streść dotychczasową rozmowę, aby zaoszczędzić tokeny",
    "/init": "przeskanuj całe repozytorium i zbuduj bazę wiedzy o plikach",
    "/cost": "pokaż dokładne statystyki zużycia tokenów oraz koszty sesji",
    "/ide": "wyświetl obecny status połączenia z Twoim środowiskiem IDE",
    "/auto": "przełącz w tryb automatyczny (bez pytania o zgody na pliki)",
    "/code": "przełącz w tryb kodowania (pyta o zgodę przed edycją)",
    "/plan": "przełącz w tryb planowania (tylko czyta pliki i planuje)",
    "/sessions": "zarządzaj sesjami kontekstowymi i powróć do starego stanu",
    "/quit": "zakończ działanie programu i zamknij okno terminala"
}
class CMDAICompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        if "@" in text:
            # Simple file completion
            prefix = text.split("@")[-1]
            try:
                dirname = os.path.dirname(prefix) or "."
                basename = os.path.basename(prefix)
                for f in os.listdir(dirname):
                    if f.startswith(basename):
                        path = os.path.join(dirname, f).replace("\\", "/")
                        if path.startswith("./"):
                            path = path[2:]
                        yield Completion(path, start_position=-len(basename))
            except Exception:
                pass
class InputHandler:
    def __init__(self, history_file="~/.cmdai2/history", thinking_idx=1):
        self.history_file = os.path.expanduser(history_file)
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        self.bindings = KeyBindings()
        self.mode_index = 0
        self.modes = ["code", "auto", "plan"]
        self.thinking_expanded = True
        self.thinking_levels = [
            ("· Low", 1024, "Pominięty (max 1 linia na plik)", "Brak sub-drzew", "Brak wymuszonych akcji"),
            ("◐ Medium", 2048, "2 pola: ROZUMIEM + PLAN", "Brak sub-drzew", "Search callerów (tak), Build (nie)"),
            ("◑ High", 4096, "4 pola: ROZ. + OPCJE + WYBÓR + PLAN", "Sub-drzewa rzadko", "Search callerów (tak), Build (tak)"),
            ("◕ Ultra", 8192, "6 pól (z RYZYKIEM)", "Sub-drzewa zawsze", "Wszystko + Identyfikacja ryzyka"),
            ("● Extreme", 16384, "6 pól + Re-walidacja na końcu", "Sub-drzewa i sub-sub zawsze", "Testy po build + osobny krok re-walidacji")
        ]
        self.thinking_idx = thinking_idx
        
        self.cmd_index = 0
        self.cmd_scroll = 0
        
        from prompt_toolkit.filters import Condition
        
        @Condition
        def is_slash_command():
            text = self.session.default_buffer.text if hasattr(self, 'session') else ""
            return text.startswith("/")
        
        @self.bindings.add('s-tab')
        def _(event):
            self.mode_index = (self.mode_index + 1) % len(self.modes)
            event.app.invalidate()
            
        @self.bindings.add('c-e')
        def _(event):
            self.thinking_expanded = not self.thinking_expanded
            
        @self.bindings.add('c-t')
        def _(event):
            self.thinking_idx = (self.thinking_idx + 1) % len(self.thinking_levels)
            event.app.invalidate()
            
        @self.bindings.add('tab', filter=is_slash_command)
        def _(event):
            text = event.app.current_buffer.text
            matches = [cmd for cmd in COMMANDS.keys() if cmd.startswith(text.lstrip())]
            if matches and 0 <= self.cmd_index < len(matches):
                event.app.current_buffer.text = matches[self.cmd_index] + " "
                event.app.current_buffer.cursor_position = len(event.app.current_buffer.text)
        @self.bindings.add('up', filter=is_slash_command)
        def _(event):
            text = event.app.current_buffer.text
            matches = [cmd for cmd in COMMANDS.keys() if cmd.startswith(text.lstrip())]
            if matches:
                self.cmd_index = max(0, self.cmd_index - 1)
                
        @self.bindings.add('down', filter=is_slash_command)
        def _(event):
            text = event.app.current_buffer.text
            matches = [cmd for cmd in COMMANDS.keys() if cmd.startswith(text.lstrip())]
            if matches:
                self.cmd_index = min(len(matches) - 1, self.cmd_index + 1)
                
        @self.bindings.add('enter', filter=is_slash_command)
        def _(event):
            text = event.app.current_buffer.text
            word = text.lstrip()
            # If exact match, just run it
            if word in COMMANDS:
                event.app.current_buffer.validate_and_handle()
            else:
                matches = [cmd for cmd in COMMANDS.keys() if cmd.startswith(word)]
                # If not exact match but selected, complete it
                if matches and 0 <= self.cmd_index < len(matches):
                    event.app.current_buffer.text = matches[self.cmd_index]
                    event.app.current_buffer.cursor_position = len(event.app.current_buffer.text)
                else:
                    event.app.current_buffer.validate_and_handle()
                    
        @self.bindings.add('enter', filter=~is_slash_command)
        def _(event):
            event.app.current_buffer.validate_and_handle()
            
        @self.bindings.add('escape', 'enter')
        def _(event):
            event.app.current_buffer.insert_text('\n')
            
        @self.bindings.add('c-v')
        def _(event):
            try:
                import ctypes
                ctypes.windll.user32.OpenClipboard(0)
                handle = ctypes.windll.user32.GetClipboardData(13) # 13 is CF_UNICODETEXT
                if handle:
                    ptr = ctypes.windll.kernel32.GlobalLock(handle)
                    data = ctypes.c_wchar_p(ptr).value
                    ctypes.windll.kernel32.GlobalUnlock(handle)
                    if data:
                        event.app.current_buffer.insert_text(data)
                ctypes.windll.user32.CloseClipboard()
            except Exception:
                try:
                    ctypes.windll.user32.CloseClipboard()
                except:
                    pass
        self.session = PromptSession(
            history=FileHistory(self.history_file),
            completer=CMDAICompleter(),
            key_bindings=self.bindings,
            style=Style.from_dict({
                'prompt': '#D97757 bold',
                'bottom-toolbar': 'default',
            }),
            complete_style=CompleteStyle.READLINE_LIKE,
            complete_while_typing=False,
            erase_when_done=True
        )
    def get_input(self, model_name: str = "model", tokens: int = 0, max_tokens: int = 32768) -> str:
        import shutil
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit import print_formatted_text
        from prompt_toolkit.layout.processors import Processor, Transformation
        from prompt_toolkit.utils import get_cwidth
        
        width = shutil.get_terminal_size().columns - 2
        top = "╭" + "─" * (width - 2) + "╮"
        
        handler = self
        
        class WrappingBottomProcessor(Processor):
            def apply_transformation(self, ti):
                term_width = shutil.get_terminal_size().columns - 1
                W = width - 5
                if W < 10: 
                    return Transformation(ti.fragments)
                
                new_fragments = []
                if ti.lineno > 0:
                    new_fragments.append(('fg:#D97757', '│   '))
                    
                current_line_len = 0
                
                for style, text in ti.fragments:
                    for char in text:
                        if char == '\n':
                            pad = W - current_line_len
                            new_fragments.append(('', ' ' * pad))
                            new_fragments.append(('fg:#D97757', '│'))
                            new_fragments.append(('', ' ' * (term_width - width)))
                            new_fragments.append(('fg:#D97757', '│   '))
                            current_line_len = 0
                            continue
                            
                        cw = get_cwidth(char)
                        if current_line_len + cw > W:
                            pad = W - current_line_len
                            if pad > 0:
                                new_fragments.append(('', ' ' * pad))
                            new_fragments.append(('fg:#D97757', '│'))
                            new_fragments.append(('', ' ' * (term_width - width)))
                            new_fragments.append(('fg:#D97757', '│   '))
                            current_line_len = 0
                            
                        new_fragments.append((style, char))
                        current_line_len += cw
                        
                pad = W - current_line_len
                if pad > 0:
                    new_fragments.append(('', ' ' * pad))
                new_fragments.append(('fg:#D97757', '│'))
                
                if ti.lineno == ti.document.line_count - 1:
                    new_fragments.append(('', ' ' * (term_width - width)))
                    
                    bottom_len = width
                    if bottom_len > 2:
                        current_bottom = "╰" + "─" * (bottom_len - 2) + "╯"
                        new_fragments.append(('fg:#D97757', current_bottom))
                        
                    new_fragments.append(('', ' ' * (term_width - width)))
                    mode_sym = {"code": "⏵ code", "auto": "⏵⏵ auto", "plan": "⏸ plan"}[handler.modes[handler.mode_index]]
                    think_name = handler.thinking_levels[handler.thinking_idx][0]
                    
                    pct = (tokens / max_tokens) * 100 if max_tokens > 0 else 0
                    bar_len = 10
                    filled_len = int((pct / 100) * bar_len)
                    filled_len = min(bar_len, max(0, filled_len))
                    bar = "█" * filled_len + "░" * (bar_len - filled_len)
                    
                    pct_str = f"{model_name}: ctx [{bar}] {pct:.0f}% ({tokens}/{max_tokens})"
                    pct_style = 'fg:red' if pct >= 80 else ('fg:#D97757' if pct >= 50 else 'fg:gray')
                    
                    status_left = f"  {mode_sym} · vulkan · {think_name} · "
                    new_fragments.append(('fg:gray', status_left))
                    new_fragments.append((pct_style, pct_str))
                    
                return Transformation(new_fragments)
        
        # Prevent prompt_toolkit from forcing a 7-line gap for autocomplete menus
        self.session.reserve_space_for_menu = 0
            
        def get_prompt():
            text = self.session.default_buffer.text
            lines = []
            
            if text.startswith("/"):
                word = text.lstrip()
                matches = [(cmd, desc) for cmd, desc in COMMANDS.items() if cmd.startswith(word)]
                if not matches and word in COMMANDS:
                    matches = [(word, COMMANDS[word])]
                    
                if matches:
                    self.cmd_index = min(self.cmd_index, len(matches) - 1)
                    if self.cmd_index < self.cmd_scroll:
                        self.cmd_scroll = self.cmd_index
                    elif self.cmd_index >= self.cmd_scroll + 4:
                        self.cmd_scroll = self.cmd_index - 3
                        
                visible_matches = matches[self.cmd_scroll : self.cmd_scroll + 4]
                
                for i, (cmd, desc) in enumerate(visible_matches):
                    actual_idx = self.cmd_scroll + i
                    # Truncate description if terminal is too narrow
                    avail_width = width - 20
                    if len(desc) > avail_width:
                        desc = desc[:avail_width-3] + "..."
                        
                    if actual_idx == self.cmd_index:
                        lines.append(f"<style bg='#333333' fg='#ffffff'>  {cmd.ljust(15)} {desc} </style>")
                    else:
                        lines.append(f"<style fg='gray'>  {cmd.ljust(15)} {desc} </style>")
            else:
                self.cmd_index = 0
                self.cmd_scroll = 0
                    
            empty_lines = 2 - len(lines)
            if empty_lines < 0:
                empty_lines = 0
                
            prompt_str = "\n" * empty_lines
            if lines:
                prompt_str += "\n".join(lines) + "\n"
                
            prompt_str += f"<style fg='#D97757'>{top}</style>\n<style fg='#D97757'>│ </style><b>&gt; </b>"
            return HTML(prompt_str)
            
        def get_continuation(width, line_number, is_soft_wrap):
            return []
            
        try:
            res = self.session.prompt(
                get_prompt, 
                multiline=True,
                prompt_continuation=get_continuation,
                reserve_space_for_menu=0,
                input_processors=[WrappingBottomProcessor()]
            )
            return res
        except KeyboardInterrupt:
            return ""
        except EOFError:
            return "/quit"
        except Exception as e:
            if type(e).__name__ == "NoConsoleScreenBufferError":
                print("\n[Ostrzeżenie: Środowisko nie posiada pełnego bufora konsoli (częste w terminalach IDE). Używam trybu uproszczonego]")
                return input("> ")
            raise
            
    def get_mode(self) -> str:
        return self.modes[self.mode_index]
