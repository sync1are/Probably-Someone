from ollama import Client
import os
from dotenv import load_dotenv
import json
from tool_handlers import execute_tool


load_dotenv()

# Init client
client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.getenv('OLLAMA_API_KEY')}
)

# Load tools from tools.json
with open('tools.json', 'r') as f:
    tools_data = json.load(f)
    available_tools = tools_data['tools']

print("🤖 AI Assistant Started (Text-only mode)")
print("📸 Screenshot tool enabled - try 'what's on my screen?'")
print("Type 'quit' or 'exit' to stop\n")

conversation_history = []

while True:
    user_input = input("You: ").strip()

    if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
        print("👋 Goodbye!")
        break

    if not user_input:
        continue

    conversation_history.append({
        'role': 'user',
        'content': user_input
    })

    # Call LLM with tools
    print("🤖 AI: ", end="", flush=True)
    
    response = client.chat(
        model='gpt-oss:120b-cloud',
        messages=conversation_history,
        tools=available_tools,
        stream=False
    )

    message = response['message']
    
    # Check if LLM wants to use a tool
    if message.get('tool_calls'):
        print("\n🔧 Using tools...")
        
        # Process all tool calls
        for tool_call in message['tool_calls']:
            tool_name = tool_call['function']['name']
            tool_args = tool_call['function']['arguments']
            
            print(f"  → Calling {tool_name}...")
            
            # Execute the tool
            tool_result = execute_tool(tool_name, tool_args)
            
            if tool_result.get('success'):
                print(f"  ✓ {tool_name} completed")
                
                # For screenshot, prepare the image for the LLM
                if tool_name == "take_screenshot" and 'image_base64' in tool_result:
                    # Add tool response to conversation
                    conversation_history.append(message)
                    conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps({
                            'success': True,
                            'message': f"Screenshot captured: {tool_result['width']}x{tool_result['height']}"
                        })
                    })
                    
                    # Add image to the message for vision model
                    conversation_history.append({
                        'role': 'user',
                        'content': 'Here is the screenshot. Please analyze it and answer my question.',
                        'images': [tool_result['image_base64']]
                    })
                else:
                    # Regular tool response
                    conversation_history.append(message)
                    conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result)
                    })
            else:
                print(f"  ✗ {tool_name} failed: {tool_result.get('error')}")
                conversation_history.append(message)
                conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps(tool_result)
                })
        
        # Get final response from LLM after tool execution
        print("\n🤖 AI: ", end="", flush=True)
        
        # Check if last message has images - use vision model if so
        has_images = conversation_history and conversation_history[-1].get('images')
        model_to_use = 'qwen3-vl:235b-instruct-cloud' if has_images else 'gpt-oss:120b-cloud'
        
        if has_images:
            print("[Analyzing screenshot with Qwen3-VL]\n")
        
        response = client.chat(
            model=model_to_use,
            messages=conversation_history,
            stream=True
        )
        
        full_response = ""
        for part in response:
            chunk = part['message']['content']
            print(chunk, end='', flush=True)
            full_response += chunk
        
        print("\n")
        
        conversation_history.append({
            'role': 'assistant',
            'content': full_response
        })
        
    else:
        # No tool calls - regular response
        response_stream = client.chat(
            model='qwen3-vl:235b-instruct-cloud',
            messages=conversation_history,
            stream=True
        )
        
        full_response = ""
        for part in response_stream:
            chunk = part['message']['content']
            print(chunk, end='', flush=True)
            full_response += chunk

        print("\n")
        
        conversation_history.append({
            'role': 'assistant',
            'content': full_response
        })
