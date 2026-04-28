"""Ollama and NVIDIA NIM LLM client setup and management."""

from ollama import chat
import json
import os


class LLMClient:
    """Wrapper for Ollama API and NVIDIA NIM client (via openai SDK)."""

    def __init__(self, backend="ollama"):
        self.backend = backend.lower()

        if self.backend in ["nvidia", "lm_studio"]:
            from openai import OpenAI
            base_url = "https://integrate.api.nvidia.com/v1" if self.backend == "nvidia" else "http://localhost:1234/v1"
            api_key = os.getenv('NVIDIA_API_KEY', '') if self.backend == "nvidia" else "lm-studio"
            self.oai_client = OpenAI(
                base_url=base_url,
                api_key=api_key
            )

    def chat(self, model, messages, tools=None, stream=False):
        """Send a chat request to the LLM backend."""
        if self.backend in ["nvidia", "lm_studio"]:
            return self._nvidia_chat(model, messages, tools, stream)

        # think=False explicitly passed for ollama
        return chat(
            model=model,
            messages=messages,
            tools=tools,
            stream=stream,
            think=False
        )

    # ------------------------------------------------------------------
    # NVIDIA path — uses the official openai SDK against NVIDIA NIM's
    # OpenAI-compatible endpoint.  All message conversion is done here
    # so app.py can keep its Ollama-style history format unchanged.
    # ------------------------------------------------------------------

    def _prepare_messages_for_nvidia(self, messages):
        """
        Convert Ollama-style conversation history to OpenAI format for NVIDIA.
        - assistant tool_calls: add id + type, serialize arguments → JSON string
        - tool results: add tool_call_id
        - strip unsupported keys (images, etc.)
        """
        prepared = []
        last_tool_call_ids = []

        for msg in messages:
            msg = dict(msg)

            if msg.get('role') == 'assistant' and msg.get('tool_calls'):
                openai_tcs = []
                last_tool_call_ids = []
                for i, tc in enumerate(msg['tool_calls']):
                    fn = tc.get('function', {})
                    args = fn.get('arguments', {})
                    if isinstance(args, dict):
                        args = json.dumps(args)
                    call_id = f"call_{i}"
                    last_tool_call_ids.append(call_id)
                    openai_tcs.append({
                        "id": call_id,
                        "type": "function",
                        "function": {"name": fn.get('name', ''), "arguments": args}
                    })
                msg['tool_calls'] = openai_tcs
                if msg.get('content') is None:
                    msg['content'] = ''

            elif msg.get('role') == 'tool':
                tool_call_id = last_tool_call_ids.pop(0) if last_tool_call_ids else "call_0"
                msg['tool_call_id'] = tool_call_id

            images = msg.pop('images', None)
            if images and isinstance(images, list):
                # Convert standard content to a list of dicts for OpenAI vision format
                original_content = msg.get('content', '')
                content_list = []
                if original_content:
                    content_list.append({"type": "text", "text": original_content})

                # Add each base64 image
                for img in images:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img}"
                        }
                    })

                msg['content'] = content_list

            prepared.append(msg)

        return prepared

    def _nvidia_chat(self, model, messages, tools, stream):
        nvidia_messages = self._prepare_messages_for_nvidia(messages)

        kwargs = {
            "model": model,
            "messages": nvidia_messages,
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 8192,
            "stream": stream,
        }

        # Only send reasoning-suppression params for models that support them (e.g. Qwen)
        if "qwen" in model.lower():
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": False},
                "reasoning_budget": 0,
            }

        if tools:
            kwargs["tools"] = tools

        completion = self.oai_client.chat.completions.create(**kwargs)

        if stream:
            return self._nvidia_stream_generator(completion)
        else:
            choice = completion.choices[0]
            msg = choice.message

            # Normalize tool_calls → Ollama dict format (args as dict not string)
            normalized_tcs = []
            for tc in (msg.tool_calls or []):
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                normalized_tcs.append({
                    "function": {"name": tc.function.name, "arguments": args}
                })

            return {
                "message": {
                    "role": msg.role,
                    "content": msg.content or "",
                    "tool_calls": normalized_tcs
                }
            }

    def _nvidia_stream_generator(self, completion):
        """Yield content chunks and accumulate tool calls if any."""
        import re
        buffer = ""
        in_tool_call = False
        tool_calls_dict = {}

        for chunk in completion:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # Accumulate OpenAI-native tool calls deltas
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {"name": "", "arguments": ""}
                    if tc.function.name:
                        tool_calls_dict[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_calls_dict[idx]["arguments"] += tc.function.arguments
                continue

            # Skip internal reasoning tokens
            if getattr(delta, "reasoning_content", None):
                continue
            content = delta.content or ""
            buffer += content

            # Detect entry into a <tool_call> block
            if not in_tool_call and "<tool_call>" in buffer:
                in_tool_call = True
                # Yield everything before the tag
                before = buffer[:buffer.index("<tool_call>")]
                if before:
                    yield {"message": {"content": before}}
                buffer = buffer[buffer.index("<tool_call>"):]

            if in_tool_call:
                # Wait until the closing tag arrives in the buffer
                if "</tool_call>" in buffer:
                    # Strip the complete block, keep any trailing text
                    buffer = re.sub(r"<tool_call>.*?</tool_call>", "", buffer, flags=re.DOTALL)
                    in_tool_call = False
                    # Fall through to yield remaining buffer below
                else:
                    continue  # Still accumulating the tag — don't yield yet

            if buffer and not in_tool_call:
                yield {"message": {"content": buffer}}
                buffer = ""

        # Flush remainder
        if buffer and not in_tool_call:
            yield {"message": {"content": buffer}}

        # If any native tool calls were accumulated, yield them at the very end
        if tool_calls_dict:
            formatted_tcs = []
            for k in sorted(tool_calls_dict.keys()):
                args_str = tool_calls_dict[k]["arguments"]
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                formatted_tcs.append({
                    "function": {
                        "name": tool_calls_dict[k]["name"],
                        "arguments": args
                    }
                })
            yield {"message": {"content": "", "tool_calls": formatted_tcs}}
