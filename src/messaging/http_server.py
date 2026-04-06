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


def run_server(host='0.0.0.0', port=5000):
    """Run the Flask server."""
    print(f"[HTTP Server] Starting on {host}:{port}")
    print(f"[HTTP Server] WhatsApp bridge should connect to http://localhost:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_server()
