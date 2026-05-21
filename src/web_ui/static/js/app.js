document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation ---
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));
            
            item.classList.add('active');
            document.getElementById(tabId).classList.add('active');
            
            if (tabId === 'tools') loadTools();
            if (tabId === 'settings') loadSettings();
            if (tabId === 'services') loadServices();
        });
    });

    // --- Console / Chat ---
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const clearChatBtn = document.getElementById('clear-chat');

    function appendMessage(role, content, isThinking = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
        if (isThinking) {
            msgDiv.innerHTML = `<div class="thinking">ARIA is thinking<span></span><span></span><span></span></div>`;
            msgDiv.id = 'thinking-indicator';
        } else {
            msgDiv.innerHTML = `<div class="bubble">${content}</div>`;
        }
        
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return msgDiv;
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        userInput.value = '';
        appendMessage('user', message);
        const thinkingIndicator = appendMessage('assistant', '', true);

        let assistantMsgDiv = null;
        let assistantBubble = null;

        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            thinkingIndicator.remove();
            assistantMsgDiv = document.createElement('div');
            assistantMsgDiv.className = 'message assistant';
            assistantBubble = document.createElement('div');
            assistantBubble.className = 'bubble';
            assistantMsgDiv.appendChild(assistantBubble);
            chatHistory.appendChild(assistantMsgDiv);

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            const event = line.match(/event: (.*)/)?.[1] || 'token'; // Simple fallback logic

                            // Better parsing for SSE format
                        } catch (e) {}
                    }
                }
                
                // Simplified SSE parsing for now
                const events = chunk.split('\n\n');
                for (const eventStr of events) {
                    if (!eventStr.trim()) continue;
                    
                    const eventMatch = eventStr.match(/event: (.*)/);
                    const dataMatch = eventStr.match(/data: (.*)/);
                    
                    if (eventMatch && dataMatch) {
                        const event = eventMatch[1];
                        const data = JSON.parse(dataMatch[1]);
                        
                        if (event === 'token') {
                            assistantBubble.innerText += data;
                        } else if (event === 'permission_request') {
                            const prompt = document.createElement('div');
                            prompt.className = 'permission-prompt';
                            prompt.innerHTML = `
                                <div class="permission-text">
                                    ⚠️ <b>Permission Request</b><br>
                                    ARIA wants to use <b>${data.name}</b><br>
                                    <small>${JSON.stringify(data.args)}</small>
                                </div>
                                <div class="permission-actions">
                                    <button class="btn btn-primary btn-sm" onclick="sendPermission('${data.request_id}', true, this)">Allow</button>
                                    <button class="btn btn-danger btn-sm" onclick="sendPermission('${data.request_id}', false, this)">Deny</button>
                                </div>
                            `;
                            assistantMsgDiv.appendChild(prompt);
                        } else if (event === 'final_stats') {
                            const metadata = document.createElement('div');
                            metadata.className = 'message-metadata';
                            metadata.innerHTML = `
                                <div class="metadata-item">⏱️ <span>${data.duration}s</span></div>
                                <div class="metadata-item">📥 <span>${data.prompt_tokens}</span></div>
                                <div class="metadata-item">📤 <span>${data.eval_tokens}</span></div>
                            `;
                            assistantBubble.appendChild(metadata);
                        } else if (event === 'tool_call') {
                            const details = document.createElement('details');
                            details.className = 'tool-call';
                            details.innerHTML = `<summary>Tool: ${data.name}</summary><div class="tool-result">Arguments: ${JSON.stringify(data.args, null, 2)}</div>`;
                            assistantMsgDiv.appendChild(details);
                        } else if (event === 'tool_result') {
                            const lastDetails = assistantMsgDiv.querySelector('details:last-of-type');
                            if (lastDetails) {
                                lastDetails.innerHTML += `<div class="tool-result">Result: ${JSON.stringify(data.result, null, 2)}</div>`;
                            }
                        }
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    }
                }
            }
        } catch (error) {
            if (thinkingIndicator) thinkingIndicator.remove();
            appendMessage('assistant', `Error: ${error.message}`);
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    clearChatBtn.addEventListener('click', () => {
        chatHistory.innerHTML = `
            <div class="message assistant">
                <div class="bubble">History cleared. How can I help you?</div>
            </div>
        `;
    });

    // --- Logs ---
    const logContainer = document.getElementById('log-container');
    const clearLogsBtn = document.getElementById('clear-logs');

    function startLogStream() {
        const eventSource = new EventSource('/api/logs/stream');
        eventSource.onmessage = (event) => {
            const log = JSON.parse(event.data);
            appendLog(log);
        };
        eventSource.onerror = () => {
            eventSource.close();
            setTimeout(startLogStream, 2000); // Reconnect after 2s
        };
    }

    function appendLog(log) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${log.type.toLowerCase()}`;
        
        let content = '';
        if (log.type === 'user_query') {
            content = `👤 USER: ${log.data.content}`;
        } else if (log.type === 'tool_call') {
            content = `🛠️ TOOL CALL: ${log.data.name}\nArgs: ${JSON.stringify(log.data.args, null, 2)}`;
        } else if (log.type === 'tool_result') {
            const success = log.data.result.success;
            content = `⚙️ TOOL RESULT (${log.data.name}): ${success ? 'Success' : 'Failed'}\nOutput: ${JSON.stringify(log.data.result, null, 2)}`;
        } else if (log.type === 'response_complete') {
            content = `✅ COMPLETE | Prompt: ${log.data.prompt_tokens} | Eval: ${log.data.eval_tokens}`;
        } else if (log.type === 'error') {
            content = `❌ ERROR: ${log.data.error}`;
        } else if (log.type === 'permission_request') {
            content = `⚠️ PERMISSION REQUEST: ${log.data.name}\nArgs: ${JSON.stringify(log.data.args, null, 2)}`;
        } else if (log.type === 'permission_result') {
            content = `⚠️ PERMISSION ${log.data.granted ? 'GRANTED' : 'DENIED'}: ${log.data.name}`;
        } else {
            content = `${log.type.toUpperCase()}: ${JSON.stringify(log.data)}`;
        }

        logEntry.innerHTML = `<span class="timestamp">[${log.timestamp}]</span><span class="type">${log.type.toUpperCase()}</span>\n${content}`;
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    clearLogsBtn.addEventListener('click', () => {
        logContainer.innerHTML = '';
    });

    window.sendPermission = async (requestId, granted, btn) => {
        const actions = btn.parentElement;
        actions.innerHTML = `<span class="text-muted">${granted ? 'Approved' : 'Denied'}</span>`;
        
        await fetch('/api/chat/permission', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: requestId, granted })
        });
    };

    // --- Tools ---
    const toolsGrid = document.getElementById('tools-grid');
    const toolSearch = document.getElementById('tool-search');
    const toolStats = document.getElementById('tool-stats');

    async function loadTools() {
        const response = await fetch('/api/tools');
        const tools = await response.json();
        renderTools(tools);
    }

    function renderTools(tools) {
        toolsGrid.innerHTML = '';
        const categories = {};
        
        tools.forEach(tool => {
            if (!categories[tool.category]) categories[tool.category] = [];
            categories[tool.category].push(tool);
        });

        const sortedCategories = Object.keys(categories).sort();
        
        let enabledCount = 0;
        sortedCategories.forEach(cat => {
            const catSection = document.createElement('div');
            catSection.className = 'tool-category-section';
            catSection.innerHTML = `<h2>${cat} (${categories[cat].length})</h2>`;
            toolsGrid.appendChild(catSection);

            categories[cat].forEach(tool => {
                if (tool.enabled) enabledCount++;
                const card = document.createElement('div');
                card.className = 'tool-card';
                card.innerHTML = `
                    <div class="tool-card-header">
                        <span class="tool-name">${tool.name}</span>
                        <label class="toggle">
                            <input type="checkbox" ${tool.enabled ? 'checked' : ''} onchange="toggleTool('${tool.name}', this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="tool-desc" title="${tool.description}">${tool.description}</div>
                `;
                toolsGrid.appendChild(card);
            });
        });

        toolStats.innerText = `${tools.length} tools · ${enabledCount} enabled · ${tools.length - enabledCount} disabled`;
    }

    window.toggleTool = async (name, enabled) => {
        await fetch(`/api/tools/${name}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        loadTools();
    };

    toolSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.tool-card').forEach(card => {
            const name = card.querySelector('.tool-name').innerText.toLowerCase();
            const desc = card.querySelector('.tool-desc').innerText.toLowerCase();
            card.style.display = (name.includes(query) || desc.includes(query)) ? 'flex' : 'none';
        });
        // Hide categories with no visible tools
        document.querySelectorAll('.tool-category-section').forEach(section => {
            let next = section.nextElementSibling;
            let hasVisible = false;
            while (next && !next.classList.contains('tool-category-section')) {
                if (next.style.display !== 'none') {
                    hasVisible = true;
                    break;
                }
                next = next.nextElementSibling;
            }
            section.style.display = hasVisible ? 'flex' : 'none';
        });
    });

    // --- Settings ---
    const settingsForm = document.getElementById('settings-form');
    const ttsSpeed = document.getElementById('tts-speed');
    const ttsSpeedVal = document.getElementById('tts-speed-val');

    async function loadSettings() {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        document.getElementById('active-backend').value = settings.active_backend;
        document.getElementById('model-ollama').value = settings.models.ollama;
        document.getElementById('model-nvidia').value = settings.models.nvidia;
        document.getElementById('ollama-host').value = settings.ollama_host;
        document.getElementById('tts-voice').value = settings.tts.voice;
        document.getElementById('tts-speed').value = settings.tts.speed;
        document.getElementById('tts-speed-val').innerText = settings.tts.speed;
        document.getElementById('browser-headless').checked = settings.behavior.browser_headless;
    }

    ttsSpeed.addEventListener('input', (e) => {
        ttsSpeedVal.innerText = e.target.value;
    });

    settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const settings = {
            active_backend: document.getElementById('active-backend').value,
            models: {
                ollama: document.getElementById('model-ollama').value,
                nvidia: document.getElementById('model-nvidia').value,
                lm_studio: "local-model" // Keep existing
            },
            ollama_host: document.getElementById('ollama-host').value,
            tts: {
                voice: document.getElementById('tts-voice').value,
                speed: parseFloat(document.getElementById('tts-speed').value),
                sample_rate: 24000
            },
            behavior: {
                browser_headless: document.getElementById('browser-headless').checked,
                asr_hotkey: "ctrl+shift"
            },
            disabled_tools: [] // Server will preserve this if we don't send it, but better fetch first
        };
        
        // Fetch current to preserve disabled_tools
        const currResp = await fetch('/api/settings');
        const curr = await currResp.json();
        settings.disabled_tools = curr.disabled_tools;

        const response = await fetch('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            alert('Settings applied successfully!');
        }
    });

    // --- Services ---
    const servicesList = document.getElementById('services-list');

    async function loadServices() {
        const response = await fetch('/api/services/status');
        const status = await response.json();
        renderServices(status);
    }

    function renderServices(status) {
        servicesList.innerHTML = '';
        
        const serviceNames = {
            tts_server: "TTS Server",
            whatsapp_bridge: "WhatsApp Bridge",
            discord_bot: "Discord Bot",
            instagram_bot: "Instagram Bot",
            messaging_http: "Messaging HTTP"
        };

        Object.keys(status).forEach(id => {
            const info = status[id];
            const card = document.createElement('div');
            card.className = 'service-card';
            card.innerHTML = `
                <div class="service-info">
                    <div class="service-title-row">
                        <span class="status-dot ${info.running ? 'active' : ''}"></span>
                        <span class="service-name">${serviceNames[id]}</span>
                    </div>
                    <div class="service-details">
                        ${info.running ? `Running (PID: ${info.pid})` : 'Stopped'} 
                        ${info.port ? `· Port ${info.port}` : ''}
                    </div>
                </div>
                <div class="service-actions">
                    <button class="btn ${info.running ? 'btn-danger' : 'btn-primary'} btn-sm" 
                            onclick="toggleService('${id}', ${info.running})">
                        ${info.running ? 'Stop' : 'Start'}
                    </button>
                </div>
            `;
            servicesList.appendChild(card);
        });
    }

    window.toggleService = async (id, running) => {
        const action = running ? 'stop' : 'start';
        await fetch(`/api/services/${id}/${action}`, { method: 'POST' });
        loadServices();
    };

    // Auto-poll services status if on services tab
    setInterval(() => {
        if (document.getElementById('services').classList.contains('active')) {
            loadServices();
        }
    }, 5000);

    // Initial load
    loadSettings();
    startLogStream();
});
