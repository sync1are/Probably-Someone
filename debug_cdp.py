import requests
import json
import websocket

tabs = requests.get('http://localhost:9222/json', timeout=2).json()
tab = next(t for t in tabs if t['type'] == 'page')
ws_url = tab['webSocketDebuggerUrl']
print(f"Connecting to: {ws_url}")

ws = websocket.create_connection(ws_url, timeout=10)  # longer timeout
print("Connected! Go ahead with the implementation")

ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot", "params": {"format": "jpeg", "quality": 50}}))
print("Sent screenshot request, waiting for response...")
result = json.loads(ws.recv())
ws.close()

if "result" in result and "data" in result["result"]:
    print(f"[OK] Got screenshot data! Length: {len(result['result']['data'])} chars")
else:
    print(f"[FAIL] Unexpected response: {list(result.keys())}")
