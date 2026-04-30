import time
import json
import os
import sys
import codecs

if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from colorama import init, Fore, Style

init(autoreset=True)

LOG_FILE = "discord_intense.log"

def format_log(entry):
    timestamp = entry.get("timestamp", "")
    event_type = entry.get("type", "")
    data = entry.get("data", {})

    time_str = f"[{timestamp}]"
    
    if event_type == "USER_QUERY":
        return f"{Style.BRIGHT}{Fore.CYAN}{time_str} 👤 USER QUERY: {data.get('content')}{Style.RESET_ALL}"
    
    elif event_type == "TOOL_CALL":
        name = data.get("name")
        args = data.get("args")
        return f"{Style.BRIGHT}{Fore.YELLOW}{time_str} 🛠️ TOOL CALL: {name}\n{Fore.LIGHTYELLOW_EX}Arguments: {json.dumps(args, indent=2)}{Style.RESET_ALL}"
    
    elif event_type == "TOOL_RESULT":
        name = data.get("name")
        res = data.get("result", {})
        success = res.get("success", False)
        color = Fore.GREEN if success else Fore.RED
        return f"{Style.BRIGHT}{color}{time_str} ⚙️ TOOL RESULT ({name}): {'Success' if success else 'Failed'}\n{Style.NORMAL}{color}Output: {json.dumps(res, indent=2)}{Style.RESET_ALL}"
    
    elif event_type == "LLM_OUTPUT_CHUNK":
        content = data.get("content", "")
        # Highlight thought process or planning if any
        return f"{Fore.LIGHTBLACK_EX}{content}{Style.RESET_ALL}"
        
    elif event_type == "RESPONSE_COMPLETE":
        p_tok = data.get('prompt_tokens', 0)
        e_tok = data.get('eval_tokens', 0)
        return f"{Style.BRIGHT}{Fore.MAGENTA}{time_str} ✅ RESPONSE COMPLETE | Prompt Tokens: {p_tok} | Eval Tokens: {e_tok}{Style.RESET_ALL}\n" + "-"*60
    
    elif event_type == "ERROR":
        err = data.get("error", "Unknown")
        return f"{Style.BRIGHT}{Fore.RED}{time_str} ❌ ERROR: {err}{Style.RESET_ALL}"

    elif event_type == "PERMISSION_REQUEST":
        name = data.get("name")
        return f"{Style.BRIGHT}{Fore.LIGHTRED_EX}{time_str} ⚠️ PERMISSION REQUEST: {name}{Style.RESET_ALL}"
        
    elif event_type == "PERMISSION_RESULT":
        name = data.get("name")
        granted = data.get("granted")
        return f"{Style.BRIGHT}{Fore.LIGHTRED_EX}{time_str} ⚠️ PERMISSION {'GRANTED' if granted else 'DENIED'}: {name}{Style.RESET_ALL}"

    return f"{time_str} {event_type}: {data}"

def main():
    print(f"{Style.BRIGHT}{Fore.GREEN}🚀 Starting Intense Logging System for ARIA Discord Bridge...{Style.RESET_ALL}")
    print(f"Watching file: {LOG_FILE}\n" + "="*60)
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            pass # create if doesn't exist

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        # Move to the end of file
        f.seek(0, 2)
        
        # We will accumulate output chunks to print them nicely without too many newlines
        chunk_buffer = ""
        
        while True:
            line = f.readline()
            if not line:
                if chunk_buffer:
                    print(chunk_buffer, end="", flush=True)
                    chunk_buffer = ""
                time.sleep(0.1)
                continue
            
            try:
                entry = json.loads(line.strip())
                
                # Special handling for streaming chunks to print them on the same line
                if entry.get("type") == "LLM_OUTPUT_CHUNK":
                    chunk_buffer += entry.get("data", {}).get("content", "")
                else:
                    if chunk_buffer:
                        # Print accumulated chunk first
                        print(f"{Fore.LIGHTBLACK_EX}{chunk_buffer}{Style.RESET_ALL}")
                        chunk_buffer = ""
                    print(format_log(entry))
            except json.JSONDecodeError:
                # If it's not JSON, print it directly
                print(line.strip())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Stopping Intense Logger.{Style.RESET_ALL}")
