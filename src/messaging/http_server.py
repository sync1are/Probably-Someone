"""
HTTP Server for WhatsApp Bridge Communication
Provides REST API for WhatsApp bridge to communicate with Python messaging controller
"""

from flask import Flask, request, jsonify
import asyncio
from src.messaging.controller import MessagingController

app = Flask(__name__)
controller = MessagingController()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'running',
        'auto_reply_enabled': controller.auto_reply_enabled,
        'stats': controller.get_stats()
    })


@app.route('/whatsapp/message', methods=['POST'])
def handle_whatsapp_message():
    """
    Handle incoming WhatsApp message from Node.js bridge.

    Expected JSON:
    {
        "message": "message text",
        "contactId": "contact ID/phone",
        "contactName": "Contact Name"
    }

    Returns:
    {
        "reply": "AI generated reply" or null
    }
    """
    data = request.json

    message = data.get('message', '')
    contact_id = data.get('contactId', '')
    contact_name = data.get('contactName', '')

    if not message or not contact_id:
        return jsonify({'error': 'Missing required fields'}), 400

    # Process message asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    reply = loop.run_until_complete(
        controller.handle_whatsapp_message(
            message_content=message,
            contact_id=contact_id,
            contact_name=contact_name
        )
    )

    loop.close()

    return jsonify({'reply': reply})


@app.route('/toggle_auto_reply', methods=['POST'])
def toggle_auto_reply():
    """
    Toggle auto-reply on/off.

    Expected JSON:
    {
        "enabled": true/false
    }
    """
    data = request.json
    enabled = data.get('enabled', True)

    controller.toggle_auto_reply(enabled)

    return jsonify({
        'auto_reply_enabled': controller.auto_reply_enabled
    })


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get messaging statistics."""
    return jsonify(controller.get_stats())


@app.route('/whitelist', methods=['GET'])
def get_whitelist():
    """Get all whitelisted contacts."""
    return jsonify(controller.whitelist_manager.get_all_whitelisted())


@app.route('/whitelist/whatsapp/add', methods=['POST'])
def add_whatsapp_contact():
    """
    Add WhatsApp contact to whitelist.

    Expected JSON:
    {
        "contact": "phone number or name"
    }
    """
    data = request.json
    contact = data.get('contact', '')

    if not contact:
        return jsonify({'error': 'Missing contact'}), 400

    controller.whitelist_manager.add_whatsapp_contact(contact)

    return jsonify({
        'success': True,
        'contact': contact
    })


@app.route('/whitelist/discord/add_user', methods=['POST'])
def add_discord_user():
    """
    Add Discord user to whitelist.

    Expected JSON:
    {
        "user_id": "Discord user ID"
    }
    """
    data = request.json
    user_id = data.get('user_id', '')

    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400

    controller.whitelist_manager.add_discord_user(user_id)

    return jsonify({
        'success': True,
        'user_id': user_id
    })


from werkzeug.serving import make_server
import threading

server_instance = None
server_lock = threading.Lock()

def start_server_in_thread(host='0.0.0.0', port=5000):
    """Start the Flask server in a daemon thread using make_server."""
    global server_instance
    with server_lock:
        if server_instance is not None:
            print("[HTTP Server] Already running.")
            return True
        
        # Check if the port is already bound
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, port))
            s.close()
        except OSError:
            print(f"[HTTP Server] Port {port} is already bound. Cannot start server.")
            return False

        server_instance = make_server(host, port, app)
        thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
        thread.start()
        print(f"[HTTP Server] Started on http://{host}:{port}")
        return True

def stop_server():
    """Shut down the Flask server instance."""
    global server_instance
    with server_lock:
        if server_instance is not None:
            print("[HTTP Server] Shutting down...")
            server_instance.shutdown()
            server_instance = None
            print("[HTTP Server] Shutdown complete.")
            return True
        return False

def run_server(host='0.0.0.0', port=5000):
    """Run the Flask server synchronously (compatibility wrapper)."""
    if start_server_in_thread(host, port):
        # Block main thread since run_server is expected to block
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_server()


if __name__ == '__main__':
    run_server()
