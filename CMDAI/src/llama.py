import json
import re
from typing import List, Dict, Any, Generator, Tuple
from llama_cpp import Llama
class LlamaModel:
    def __init__(self, model_path: str, n_ctx: int = 8192, n_gpu_layers: int = 16):
        import os
        self.model_path = os.path.abspath(model_path)
        self.n_ctx = n_ctx
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        
    def get_context_limit(self) -> int:
        return self.n_ctx
        
    def stream_chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None, **kwargs) -> Generator[Tuple[str, str, Dict], None, None]:
        """
        Streams the response from the model.
        Yields tuples of (content_chunk, thinking_chunk, tool_calls_dict)
        """
        response = self.llm.create_chat_completion(
            messages=messages,
            tools=tools,
            stream=True,
            temperature=0.3,
            repeat_penalty=1.15
        )
        
        in_thinking = False
        content_buffer = ""
        
        tool_calls = None
        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            
            if "tool_calls" in delta:
                if tool_calls is None:
                    tool_calls = delta["tool_calls"]
                else:
                    for tc in delta["tool_calls"]:
                        if "function" in tc and "arguments" in tc["function"]:
                            idx = tc["index"]
                            if idx < len(tool_calls):
                                if "arguments" not in tool_calls[idx]["function"]:
                                    tool_calls[idx]["function"]["arguments"] = ""
                                tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
            
            if "content" in delta and delta["content"]:
                content_buffer += delta["content"]
                
                while content_buffer:
                    if not in_thinking:
                        idx1 = content_buffer.find("<think>")
                        idx2 = content_buffer.find("<thinking>")
                        idx = idx1 if idx1 != -1 else idx2
                        tag_len = 7 if idx1 != -1 else 10
                        
                        if idx != -1:
                            if idx > 0:
                                yield content_buffer[:idx], "", None
                            in_thinking = True
                            content_buffer = content_buffer[idx+tag_len:]
                        else:
                            # Hold back characters that could form a tag
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
                        idx = idx1 if idx1 != -1 else idx2
                        tag_len = 8 if idx1 != -1 else 11
                        
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
                    
        if tool_calls:
            yield "", "", tool_calls
