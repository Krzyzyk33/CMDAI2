import questionary
from rich.console import Console

console = Console()

def run_models_manager(state, save_callback):
    while True:
        api_models = state.get("api_models", [])
        if not api_models:
            console.print("[yellow]Brak zapisanych modeli API.[/yellow]")
            import time; time.sleep(1.5)
            return

        choices = []
        for i, m in enumerate(api_models):
            choices.append(questionary.Choice(f"{m['name']} [{m.get('provider', 'unknown').upper()}]", value=i))
        choices.append(questionary.Choice("Wr (Wróć)", value=-1))

        selected_idx = questionary.select(
            "Zarządzanie modelami - wybierz model do edycji:",
            choices=choices
        ).ask()

        if selected_idx == -1 or selected_idx is None:
            break

        model = api_models[selected_idx]
        action = questionary.select(
            f"Edycja: {model['name']}",
            choices=["Zmień nazwę modelu", "Zmień Base URL", "Usuń model", "Wr (Wróć)"]
        ).ask()

        if action == "Zmień nazwę modelu":
            new_name = questionary.text("Podaj nową nazwę modelu:", default=model["name"]).ask()
            if new_name:
                api_models[selected_idx]["name"] = new_name
                state["api_models"] = api_models
                save_callback(state)
                console.print("[green]Zaktualizowano nazwę modelu.[/green]")
        elif action == "Zmień Base URL":
            new_url = questionary.text("Podaj nowy Base URL:", default=model.get("base_url", "")).ask()
            if new_url:
                api_models[selected_idx]["base_url"] = new_url
                state["api_models"] = api_models
                save_callback(state)
                console.print("[green]Zaktualizowano Base URL.[/green]")
        elif action == "Usuń model":
            confirm = questionary.confirm("Czy na pewno chcesz usunąć ten model?").ask()
            if confirm:
                api_models.pop(selected_idx)
                state["api_models"] = api_models
                save_callback(state)
                console.print("[green]Usunięto model z konfiguracji.[/green]")

def run_api_keys_manager(state, save_callback):
    while True:
        api_keys = state.get("api_keys", {})
        if not api_keys:
            console.print("[yellow]Brak zapisanych kluczy API.[/yellow]")
            import time; time.sleep(1.5)
            return

        choices = []
        for k in api_keys.keys():
            choices.append(questionary.Choice(f"Klucz dla: {k.upper()}", value=k))
        choices.append(questionary.Choice("Wr (Wróć)", value=None))

        selected_provider = questionary.select(
            "Zarządzanie kluczami API - wybierz dostawcę:",
            choices=choices
        ).ask()

        if not selected_provider:
            break

        action = questionary.select(
            f"Klucz dla {selected_provider.upper()}:",
            choices=["Zmień klucz", "Usuń klucz", "Wr (Wróć)"]
        ).ask()

        if action == "Zmień klucz":
            new_key = questionary.text("Podaj nowy klucz API:", default=api_keys[selected_provider]).ask()
            if new_key:
                api_keys[selected_provider] = new_key
                state["api_keys"] = api_keys
                save_callback(state)
                console.print(f"[green]Zaktualizowano klucz dla {selected_provider.upper()}.[/green]")
        elif action == "Usuń klucz":
            confirm = questionary.confirm(f"Czy na pewno usunąć klucz dla {selected_provider.upper()}?").ask()
            if confirm:
                del api_keys[selected_provider]
                state["api_keys"] = api_keys
                save_callback(state)
                console.print(f"[green]Usunięto klucz dla {selected_provider.upper()}.[/green]")
