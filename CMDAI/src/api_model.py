import json
import re
from typing import List, Dict, Any, Generator, Tuple
from openai import OpenAI
import os
class OpenAIAPIModel:
    def __init__(self, model_name: str, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1"):
        self.model_name = model_name
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.is_api = True
    def get_context_limit(self) -> int:
        return 10000000
    def stream_chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None, reasoning_budget: int = 16384) -> Generator[Tuple[str, str, Any], None, None]:
        # Convert tools to OpenAI format if provided
        openai_tools = None
        if tools:
            openai_tools = [{"type": "function", "function": t["function"]} for t in tools]
        active_tool_calls = {}
        in_thinking = False
        content_buffer = ""
        try:
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 8192,
                "stream": True,
                "timeout": 300.0
            }
            
            if "nvidia.com" in str(self.client.base_url):
                if reasoning_budget > 0:
                    kwargs["extra_body"] = {
                        "chat_template_kwargs": {
                            "enable_thinking": True
                        },
                        "reasoning_budget": reasoning_budget
                    }
                else:
                    kwargs["extra_body"] = {
                        "chat_template_kwargs": {
                            "enable_thinking": False
                        }
                    }
            if openai_tools:
                kwargs["tools"] = openai_tools
            response = self.client.chat.completions.create(**kwargs)
            
            for chunk in response:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Accumulate tool calls chunks
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in active_tool_calls:
                            active_tool_calls[idx] = {
                                "id": tc.id or f"call_{idx}",
                                "type": "function",
                                "function": {
                                    "name": tc.function.name or "",
                                    "arguments": tc.function.arguments or ""
                                }
                            }
                            # Inform user in the tree that tool generation started
                            if tc.function.name:
                                yield "", f"- Uruchamiam narzędzie: {tc.function.name}...\n", None
                        else:
                            if tc.function.name:
                                if tc.function.name not in active_tool_calls[idx]["function"]["name"]:
                                    active_tool_calls[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                active_tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                                
                
                if delta.content:
                    content_buffer += delta.content
                    
                    while content_buffer:
                        if not in_thinking:
                            idx1 = content_buffer.find("<think>")
                            idx2 = content_buffer.find("<thinking>")
                            idx3 = content_buffer.find("<|channel>thought")
                            
                            idx = idx1
                            tag_len = 7
                            if idx2 != -1 and (idx == -1 or idx2 < idx):
                                idx = idx2
                                tag_len = 10
                            if idx3 != -1 and (idx == -1 or idx3 < idx):
                                idx = idx3
                                tag_len = 18
                            
                            if idx != -1:
                                if idx > 0:
                                    yield content_buffer[:idx], "", None
                                in_thinking = True
                                content_buffer = content_buffer[idx+tag_len:]
                            else:
                                if "<" in content_buffer:
                                    last_lt = content_buffer.rfind("<")
                                    yield content_buffer[:last_lt], "", None
                                    content_buffer = content_buffer[last_lt:]
                                    break
                                else:
                                    yield content_buffer, "", None
                                    content_buffer = ""
                        else:
                            idx1 = content_buffer.find("</think>")
                            idx2 = content_buffer.find("</thinking>")
                            idx3 = content_buffer.find("<channel|>")
                            
                            idx = idx1
                            tag_len = 8
                            if idx2 != -1 and (idx == -1 or idx2 < idx):
                                idx = idx2
                                tag_len = 11
                            if idx3 != -1 and (idx == -1 or idx3 < idx):
                                idx = idx3
                                tag_len = 10
                            
                            if idx != -1:
                                if idx > 0:
                                    yield "", content_buffer[:idx], None
                                in_thinking = False
                                content_buffer = content_buffer[idx+tag_len:]
                            else:
                                if "<" in content_buffer:
                                    last_lt = content_buffer.rfind("<")
                                    yield "", content_buffer[:last_lt], None
                                    content_buffer = content_buffer[last_lt:]
                                    break
                                else:
                                    yield "", content_buffer, None
                                    content_buffer = ""
                                    
            if content_buffer:
                if in_thinking:
                    yield "", content_buffer, None
                else:
                    yield content_buffer, "", None
            
            # End of stream: yield accumulated tool calls
            if active_tool_calls:
                final_calls = []
                for idx, tc_data in active_tool_calls.items():
                    args_str = tc_data["function"]["arguments"]
                    try:
                        tc_data["function"]["arguments"] = json.loads(args_str)
                    except Exception:
                        # Keep it as string if invalid, agent.py might fix it
                        pass
                    final_calls.append(tc_data)
                
                yield "", "", final_calls
                
        except Exception as e:
            yield f"\n[API Error: {str(e)}]\n", "", None
