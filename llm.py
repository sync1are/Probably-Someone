from ollama import chat

response = chat(
  model='deepseek-r1:1.5b',
  messages=[{'role': 'user', 'content': input("Enter your message: ")}],
  think=False,
  stream=False,
)

print('Thinking:\n', response.message.thinking)
print('Answer:\n', response.message.content)