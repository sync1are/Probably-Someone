import json
import re
import time
import inspect
from typing import List, Dict, Any, Optional, Callable

from src.config import DEFAULT_MODEL, TOOLS_FILE
from src.core.llm_client import LLMClient
from src.tools.registry import execute_tool

class Agent:
    """
    Unified agent that handles the conversation loop and tool execution.
    Can be used by CLI, Discord, or other interfaces.
    """

    def __init__(self, backend="ollama", model=None, system_prompt=None, tools=None, browser_headless=True, browser_backend=None, browser_model=None):
        self.llm_client = LLMClient(backend=backend)
        self.backend = backend
        self.model = model or DEFAULT_MODEL
        self.browser_headless = browser_headless
        self.browser_backend = browser_backend or backend
        self.browser_model = browser_model or self.model
        self.conversation_history = []
        if system_prompt:
            self.conversation_history.append({"role": "system", "content": system_prompt})
        
        self.tools = tools or []
        
        # Tools that should always get direct responses (no LLM needed)
        self.direct_response_tools = [
            'spotify_pause', 'spotify_skip_next', 'spotify_skip_previous',
            'spotify_shuffle', 'spotify_repeat', 'spotify_volume',
            'spotify_like_current', 'spotify_unlike_current', 'set_system_volume',
            'adjust_system_volume', 'toggle_system_mute', 'smart_media_control',
            'set_system_brightness', 'adjust_system_brightness', 'minimize_window',
            'close_window', 'show_desktop'
        ]
        
        # Tools that need LLM for natural language responses
        self.llm_response_tools = [
            'spotify_play', 'spotify_add_to_queue', 'spotify_current_track',
            'get_important_unread_emails', 'read_specific_email'
        ]
        
        # Tools that require explicit user permission
        self.sensitive_tools = [
            'read_file', 'write_file', 'append_to_file', 'run_terminal_command',
            'close_window', 'close_all', 'send_email', 'browser_use_task',
            'read_pdf'
        ]

    def add_message(self, role: str, content: str, images: Optional[List[str]] = None):
        msg = {"role": role, "content": content}
        if images:
            msg["images"] = images
        self.conversation_history.append(msg)

    async def run(self, user_input: str, output_callback: Callable[[str], Any], tool_callback: Optional[Callable[[str, Dict], Any]] = None, tool_result_callback: Optional[Callable[[str, Dict], Any]] = None, permission_callback: Optional[Callable[[str, Dict], Any]] = None):
        """
        Main execution loop.
        output_callback: function to call with chunks of text response.
        tool_callback: function to call when a tool is about to be executed.
        tool_result_callback: function to call after a tool has executed.
        permission_callback: function to call before a sensitive tool executes.
        """
        self.add_message("user", user_input)
        
        # Initial chat call
        response_stream = self.llm_client.chat(
            model=self.model,
            messages=self.conversation_history,
            tools=self.tools,
            stream=True
        )

        message = await self._process_stream(response_stream, output_callback)
        
        loop_count = 0
        max_loops = 5

        while message.get('tool_calls') and loop_count < max_loops:
            loop_count += 1
            
            final_response_stream, direct_output, is_writing = await self._process_tool_calls(
                message, 
                tool_callback,
                tool_result_callback,
                permission_callback
            )

            if direct_output:
                if inspect.iscoroutinefunction(output_callback):
                    await output_callback(direct_output)
                else:
                    output_callback(direct_output)

                self.conversation_history.append({
                    'role': 'assistant',
                    'content': direct_output
                })
                break

            # If we have a final response stream from LLM
            message = await self._process_stream(final_response_stream, output_callback)

            if not message.get('tool_calls'):
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': message.get('content', '')
                })
                break
            # else: continue loop for more tool calls

        if not message.get('tool_calls') and loop_count == 0:
            self.conversation_history.append({
                'role': 'assistant',
                'content': message.get("content", "")
            })

        return message

    async def _process_stream(self, response_stream, output_callback):
        full_content = ""
        tool_calls = []
        prompt_tokens = 0
        eval_tokens = 0
        
        for chunk in response_stream:
            # Accumulate usage statistics if present
            if 'prompt_eval_count' in chunk:
                prompt_tokens += chunk['prompt_eval_count']
            if 'eval_count' in chunk:
                eval_tokens += chunk['eval_count']

            msg = chunk.get('message', {})
            
            if msg.get('tool_calls'):
                tool_calls = msg['tool_calls']

            content = msg.get('content', '')
            if content:
                if inspect.iscoroutinefunction(output_callback):
                    await output_callback(content)
                else:
                    output_callback(content)
                full_content += content

        cleaned_content = full_content
        cleaned_content = re.sub(r'<tool_call>.*?</tool_call>', '', cleaned_content, flags=re.DOTALL)
        cleaned_content = re.sub(r'<?function=.*?(?:</tool_call>|</function>)', '', cleaned_content, flags=re.DOTALL)
        cleaned_content = cleaned_content.strip()

        return {
            "role": "assistant",
            "content": cleaned_content,
            "tool_calls": tool_calls if tool_calls else None,
            "prompt_tokens": prompt_tokens,
            "eval_tokens": eval_tokens
        }

    async def _process_tool_calls(self, message, tool_callback, tool_result_callback=None, permission_callback=None):
        # Add assistant message once before processing tool calls
        self.conversation_history.append(message)
        
        all_direct = all(
            tool_call['function']['name'] in self.direct_response_tools
            for tool_call in message['tool_calls']
        )
        
        direct_responses = []
        needs_llm = False
        screenshot_data = None
        
        for tool_call in message['tool_calls']:
            tool_name = tool_call['function']['name']
            tool_args = tool_call['function']['arguments']

            if tool_callback:
                if inspect.iscoroutinefunction(tool_callback):
                    await tool_callback(tool_name, tool_args)
                else:
                    tool_callback(tool_name, tool_args)

            # Look for file path dependencies
            if isinstance(tool_args, dict):
                for prev_msg in reversed(self.conversation_history):
                    if prev_msg.get('role') == 'tool':
                        try:
                            prev_res = json.loads(prev_msg.get('content', '{}'))
                            if prev_res.get('success') and 'filepath' in prev_res.get('data', {}):
                                prev_path = prev_res['data']['filepath']
                                for key, val in tool_args.items():
                                    if isinstance(val, str) and len(val) > 2 and val in prev_path:
                                        tool_args[key] = prev_path
                        except Exception:
                            pass

            # Check for permissions if it's a sensitive tool
            if tool_name in self.sensitive_tools and permission_callback:
                if inspect.iscoroutinefunction(permission_callback):
                    allowed = await permission_callback(tool_name, tool_args)
                else:
                    allowed = permission_callback(tool_name, tool_args)
                
                if not allowed:
                    tool_result = {"success": False, "message": f"Permission denied for {tool_name}"}
                else:
                    # Use browser-specific settings for browser tasks
                    if tool_name == "browser_use_task":
                        tool_result = await execute_tool(tool_name, tool_args, backend=self.browser_backend, model=self.browser_model, headless=self.browser_headless)
                    else:
                        tool_result = await execute_tool(tool_name, tool_args, backend=self.backend, model=self.model, headless=self.browser_headless)
            else:
                if tool_name == "browser_use_task":
                    tool_result = await execute_tool(tool_name, tool_args, backend=self.browser_backend, model=self.browser_model, headless=self.browser_headless)
                else:
                    tool_result = await execute_tool(tool_name, tool_args, backend=self.backend, model=self.model, headless=self.browser_headless)
            
            if tool_result_callback:
                if inspect.iscoroutinefunction(tool_result_callback):
                    await tool_result_callback(tool_name, tool_result)
                else:
                    tool_result_callback(tool_name, tool_result)

            if tool_result.get('success'):
                if tool_name in self.llm_response_tools:
                    needs_llm = True
                
                if tool_name in self.direct_response_tools and all_direct:
                    response_text = tool_result.get('message', 'Done')
                    direct_responses.append(response_text)
                    
                    self.conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result)
                    })
                    # We don't append assistant message here yet, it's done in the run() loop if direct
                elif tool_name == "take_screenshot" and 'image_base64' in tool_result:
                    needs_llm = True
                    screenshot_data = tool_result
                    filepath = tool_result.get('filepath')
                    msg = f"Screenshot captured: {tool_result['width']}x{tool_result['height']}"
                    if filepath:
                        msg += f" (saved to {filepath})"
                        
                    self.conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps({
                            'success': True,
                            'message': msg,
                            'filepath': filepath
                        })
                    })
                else:
                    self.conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result)
                    })
            else:
                err_txt = tool_result.get('error') or tool_result.get('message') or "Unknown error"
                needs_llm = True
                self.conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps(tool_result)
                })
        
        if screenshot_data:
            self.conversation_history.append({
                'role': 'user',
                'content': 'Analyze this screenshot.',
                'images': [screenshot_data['image_base64']]
            })

        if all_direct and direct_responses and not needs_llm:
            return None, '\n'.join(direct_responses), False
        
        is_writing_code = any(
            tool_call['function']['name'] == 'write_file'
            for tool_call in message['tool_calls']
        )

        final_response_stream = self.llm_client.chat(
            model=self.model,
            messages=self.conversation_history,
            tools=self.tools,
            stream=True
        )

        return final_response_stream, None, is_writing_code
