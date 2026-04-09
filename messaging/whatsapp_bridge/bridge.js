const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());

// In-memory log of received messages (capped at 500 to avoid unbounded growth)
const MAX_LOG_SIZE = 500;
const messageLog = [];

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true, args: ['--no-sandbox'] }
});

client.on('qr', (qr) => {
    console.log('Scan this QR code with WhatsApp:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('WhatsApp Client is ready!');
});

client.on('message', async msg => {
    console.log(`Received message: ${msg.body}`);

    // Store message in memory
    try {
        const contact = await msg.getContact();
        const entry = {
            fromId: contact.id._serialized,
            fromName: contact.name || contact.pushname || contact.number || 'Unknown',
            body: msg.body,
            date: new Date().toISOString(),
            timestamp: Date.now()
        };
        messageLog.push(entry);
        if (messageLog.length > MAX_LOG_SIZE) {
            messageLog.shift(); // Remove oldest when cap is hit
        }

        // Forward to Python backend if running
        try {
            const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));
            await fetch('http://localhost:5000/api/whatsapp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contact_id: entry.fromId,
                    contact_name: entry.fromName,
                    message: msg.body
                })
            });
        } catch (e) {
            console.error('Error forwarding to Python:', e.message);
        }
    } catch (e) {
        console.error('Error processing incoming message:', e.message);
    }
});

app.post('/api/send', async (req, res) => {
    try {
        const { to, message } = req.body;
        if (!to || !message) return res.status(400).json({ error: 'Missing to/message' });

        await client.sendMessage(to, message);
        res.json({ success: true });
    } catch (e) {
        console.error('Error sending message:', e);
        res.status(500).json({ error: e.message });
    }
});

// Add this health check endpoint so Python knows the bridge is alive
app.get('/health', (req, res) => {
    res.json({ status: 'ok', clientReady: client.info !== undefined });
});

// GET /last_message?contact=Name  — returns the most recent received message
// If ?contact= is provided, filters to messages from that contact (case-insensitive substring match)
app.get('/last_message', (req, res) => {
    const contactFilter = req.query.contact ? req.query.contact.toLowerCase() : null;

    let filtered = messageLog;
    if (contactFilter) {
        filtered = messageLog.filter(m =>
            m.fromName.toLowerCase().includes(contactFilter) ||
            m.fromId.toLowerCase().includes(contactFilter)
        );
    }

    if (filtered.length === 0) {
        const noMsgReason = contactFilter
            ? `No messages found from contact matching "${req.query.contact}".`
            : 'No messages received yet.';
        return res.status(404).json({ success: false, error: noMsgReason });
    }

    const last = filtered[filtered.length - 1];
    return res.json({ success: true, message: last });
});

// GET /messages?contact=Name&limit=10  — returns recent message history
app.get('/messages', (req, res) => {
    const contactFilter = req.query.contact ? req.query.contact.toLowerCase() : null;
    const limit = parseInt(req.query.limit, 10) || 10;

    let filtered = messageLog;
    if (contactFilter) {
        filtered = messageLog.filter(m =>
            m.fromName.toLowerCase().includes(contactFilter) ||
            m.fromId.toLowerCase().includes(contactFilter)
        );
    }

    const recent = filtered.slice(-limit);
    return res.json({ success: true, messages: recent, total: filtered.length });
});

app.post('/send', async (req, res) => {
    // Backwards compatibility for the Python script which calls /send directly
    // but sends "contact" instead of "to"
    try {
        const { contact, message } = req.body;
        const target = req.body.to || contact;
        if (!target || !message) return res.status(400).json({ error: 'Missing contact/message' });

        // Find the contact ID if they just sent a name
        let targetId = target;
        if (!target.includes('@c.us')) {
            const contacts = await client.getContacts();
            const found = contacts.find(c => c.name === target || c.pushname === target);
            if (found) {
                targetId = found.id._serialized;
            } else {
                return res.status(404).json({ error: 'Contact not found', success: false });
            }
        }

        await client.sendMessage(targetId, message);
        res.json({ success: true });
    } catch (e) {
        console.error('Error sending message:', e);
        res.status(500).json({ error: e.message, success: false });
    }
});

const PORT = process.env.WHATSAPP_BRIDGE_PORT || 3000;
const server = app.listen(PORT, () => {
    console.log(`WhatsApp Bridge running on port ${PORT}`);
});

// Handle graceful shutdown when Python process exits
process.on('SIGTERM', () => {
    console.log('SIGTERM received. Shutting down gracefully...');
    server.close(() => {
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('SIGINT received. Shutting down gracefully...');
    server.close(() => {
        process.exit(0);
    });
});

client.initialize();
