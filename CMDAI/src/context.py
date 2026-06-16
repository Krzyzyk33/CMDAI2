import os
from typing import List, Dict
SYSTEM_PROMPT = """You are CMDAI2, a highly capable AI coding assistant running locally in the terminal.
You have access to tools to read, create, edit, search and delete files. You CAN run terminal commands and bash/powershell scripts using the bash tool, but ONLY under user supervision (the user must confirm execution).
Before answering or using tools, you must output your internal thinking process between <think> and </think> tags.
Inside the <think> tags, use bullet points starting with "- " to list your steps.
Example:
<think>
- Analizuję zapytanie użytkownika...
- Sprawdzam strukturę projektu
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
26: AVAILABLE TOOLS:
{tools_desc}
UI FORMATTING RULES:
You must include the following formatted blocks in your response text to inform the user about the operations you perform. Use ONLY real data. If an operation wasn't performed yet, do NOT generate its block.
1. Read (odczyt pliku)
Format:
● Odczyt: <nazwa_pliku>
  ⎿ <N> linii
Kiedy generować: gdy odczytałeś plik (np. read_file).
Dane wymagane: nazwa pliku, liczba linii w odczytanym pliku.
2. Edit (edycja istniejącego pliku)
Format:
● Edycja: <nazwa_pliku>
  ⎿ Zmieniono <nazwa_pliku> (+<N> / -<M>)
     <numer_linii>   <treść_linii_niezmienionej>
     <numer_linii> - <treść_linii_usuniętej>
     <numer_linii> + <treść_linii_dodanej>
Kiedy generować: gdy edytujesz istniejący plik (np. edit_file). Musi być poprzedzone odczytem.
Dane wymagane: nazwa pliku, liczba dodanych (+N) i usuniętych (-M) linii, treść zmian (jak diff).
3. Write (nowy plik)
Format:
● Nowy plik: <nazwa_pliku>
  ⎿ Utworzono <nazwa_pliku> (<N> linii)
     1  <pierwsza_linia>
     2  <druga_linia>
     3  <trzecia_linia>
Kiedy generować: gdy tworzysz nowy plik. Nie nadpisuj istniejących plików tą akcją!
Dane wymagane: nazwa pliku, całkowita liczba linii, podgląd pierwszych 3 linii.
4. Bash (wykonanie komendy)
Format sukcesu:
● Komenda: <komenda>
  ⎿ OK (exit 0)
Format błędu:
● Komenda: <komenda>
  ⎿ ✗ <treść błędu> (exit <kod>)
Kiedy generować: po wykonaniu komendy w terminalu. Zawsze podaj prawdziwy exit code.
Jeżeli 3 razy z rzędu komenda się nie powiedzie, ZATRZYMAJ się i zapytaj użytkownika.
5. Search / Grep / Glob (wyszukiwanie)
Format z wynikami:
● Szukam: "<wzorzec>"
  ⎿ <N> wyników
     <plik1>:<linia>
     <plik2>:<linia>
Format bez wyników:
● Szukam: "<wzorzec>"
  ⎿ brak wyników
Kiedy generować: po użyciu narzędzi szukających. Podaj do 5 wyników.
6. TodoWrite (plan zadań)
Format:
● Plan zadań
  ⎿ [x] <zadanie zakończone>
     [ ] <zadanie do wykonania>
Kiedy generować: na starcie zadania (min. 3 kroki). Aktualizuj widget w kolejnych odpowiedziach.
7. Permission Prompt (pytanie o zgodę)
Format:
● Komenda: <komenda>
  Wykonać?
  ❯ 1. Tak
    2. Tak, nie pytaj więcej o "<typ_komendy>"
    3. Nie - powiedz co zrobić inaczej
Kiedy generować: PRZED potencjalnie destrukcyjną komendą (rm, git push --force, instalacja). Czekaj na wybór użytkownika.
8. Task / Subagent dispatch
Format:
● Zadanie: <krótki_opis>
  ⎿ Gotowe (<N> akcji · <K>k tokenów · <T>s)
Kiedy generować: przy delegowaniu większej paczki zadań.
9. Status bar (pasek stanu tury)
Podczas pracy jest automatycznie na dole ekranu: ✻ Pracuję... (<T>s · esc = przerwij)
Na koniec: ✻ Gotowe (<T>s · <K>k tokenów · <N> akcji · esc = przerwij)
PAMIĘTAJ: Zawsze generuj te bloki na podstawie rzeczywistych wyników narzędzi, NIE WYMYŚLAJ ich z góry.
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
        console.print(f"\n[{MUTED_COLOR}][Kompaktowanie pamięci kontekstu...][/]")
        compaction_prompt = "Streść tę sesję pracy dokładnie w tym formacie markdown (bez otaczających tagów):\nCel: <1-2 linie>\nDecyzje:\n- <decyzja>\nPliki:\n- <plik>: <zmiana>\nPlan:\n[x] <krok zrobiony>\n[ ] <krok do zrobienia>\nProblemy:\n- <problem>\nOgraniczenia:\n- <ograniczenie>"
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
        prompt = "You are CMDAI2, an advanced AI coding assistant."
        
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
            
        # Potężne egzekwowanie myślenia dla każdego trybu
        if thinking_desc:
            prompt += (
                f"\n\n*** THINKING LEVEL REQUIREMENTS ***\n"
                f"{thinking_desc}\n\n"
                "CRITICAL INSTRUCTION: Your output MUST begin with a <think>...</think> block analyzing the problem according to the requirements above.\n"
                "If you are instructed to use Text-Based Tool Calling, you MUST output your tool call as a JSON block immediately after the </think> tag, like this:\n"
                "```json\n{\n  \"name\": \"tool_name\",\n  \"arguments\": { ... }\n}\n```\n"
                "Do NOT output native API tool calls if they are disabled. Always write <think> before your json block!"
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
        return [self.get_system_message(tools_desc, mode, thinking_desc)] + self.messages
    def clear(self):
        self.messages = []
        self.save_history()
        
    def count_tokens(self) -> int:
        # Pomiń system prompt, żeby pasek zaczynał od 0% (pokazujemy zużycie "rozmową")
        text = " ".join([m.get("content", "") for m in self.messages if m.get("content")])
        words = len(text.split())
        return int(words * 1.3)
