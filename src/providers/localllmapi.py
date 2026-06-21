from openai import OpenAI

PROVIDER_ID = "localllmapi"
DISPLAY_NAME = "Local LLM API"
BASE_URL = ""

def match_url(url: str) -> bool:
    return '127.0.0.1' in url or 'localhost' in url or 'localllmapi' in url

def modify_chat_kwargs(kwargs: dict, reasoning_budget: int = 0) -> None:
    if "max_tokens" in kwargs:
        del kwargs["max_tokens"]
        
    # Użytkownik zaimplementował poprawny standard SSE na serwerze! Strumieniowanie aktywne.
    kwargs["stream"] = True
    kwargs["timeout"] = 120.0
    # Zabezpieczenie dla lokalnych API (Pydantic ValidationError dla tool_calls/role=tool)
    if "messages" in kwargs:
        for msg in kwargs["messages"]:
            if "tool_calls" in msg:
                del msg["tool_calls"]
            if msg.get("role") == "tool":
                msg["role"] = "user"
                msg["content"] = f"[TOOL RESPONSE]\n{msg.get('content')}\n[/TOOL RESPONSE]"
