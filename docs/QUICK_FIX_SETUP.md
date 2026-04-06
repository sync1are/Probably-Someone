# Quick Fix - Setup WhatsApp Command

## Issue
When you say "help me setup WhatsApp", it fails because dependencies aren't installed yet.

## Solution

### Step 1: Install Python Dependencies
```bash
pip install requests flask discord.py-self
```

Or use your venv:
```bash
./venv/Scripts/pip install requests flask discord.py-self
```

### Step 2: Install WhatsApp Bridge Dependencies
```bash
cd whatsapp_bridge
npm install
```

This installs the Node.js packages needed for WhatsApp (takes ~1-2 minutes).

### Step 3: Test Again
```bash
python app.py
```

Then say: **"Help me setup WhatsApp"**

Now it should work and show the QR code!

---

## What's Happening

The `setup_whatsapp` tool checks if dependencies are installed:
1. ✅ Python `requests` module
2. ⏳ Node.js packages in `whatsapp_bridge/node_modules`

If step 2 isn't done, it tells you to run `npm install`.

---

## Auto-Install Script

Create `setup.bat`:
```batch
@echo off
echo Installing dependencies...
pip install requests flask discord.py-self
cd whatsapp_bridge
npm install
echo Done!
pause
```

Run once, then everything works!

---

## After Setup

Once installed, "help me setup WhatsApp" will:
1. Start the WhatsApp bridge
2. Show QR code in terminal
3. Guide you through scanning it

✅ **Dependencies installing now in background!**
