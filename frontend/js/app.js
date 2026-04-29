/**
 * AI Research Agent — Frontend Application
 * Real-time WebSocket client for watching agents work live.
 */

// ─── State ──────────────────────────────────────
let currentResearchId = null;
let ws = null;
let eventCount = 0;

const PIPELINE_STEPS = ['planning', 'researching', 'analyzing', 'fact_checking', 'writing'];
let completedSteps = new Set();
let currentStep = null;

// ─── Agent Color Map ────────────────────────────
const AGENT_COLORS = {
    orchestrator: '#7c6cff',
    researcher:   '#48dbfb',
    analyst:      '#feca57',
    fact_checker: '#4ade80',
    writer:       '#ff6b9d',
};

const AGENT_ICONS = {
    orchestrator: '🎯',
    researcher:   '🔍',
    analyst:      '📊',
    fact_checker: '✅',
    writer:       '✍️',
};


// ─── Start Research ─────────────────────────────

async function startResearch() {
    const topicInput = document.getElementById('topic-input');
    const customInstructions = document.getElementById('custom-instructions');
    const btn = document.getElementById('btn-research');

    const topic = topicInput.value.trim();
    if (!topic) {
        topicInput.focus();
        topicInput.style.borderColor = '#f87171';
        setTimeout(() => topicInput.style.borderColor = '', 1500);
        return;
    }

    // Disable input
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Starting...';

    try {
        const response = await fetch('/api/research', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                custom_instructions: customInstructions.value.trim() || null,
            }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        currentResearchId = data.research_id;

        // Show dashboard
        showDashboard();

        // Connect WebSocket
        connectWebSocket(currentResearchId);

        // Update status
        updateStatusBadge('Researching', 'yellow');

    } catch (error) {
        console.error('Failed to start research:', error);
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🚀</span><span class="btn-text">Start Research</span>';
        alert('Failed to start research. Make sure the server is running.');
    }
}


// ─── WebSocket Connection ───────────────────────

function connectWebSocket(researchId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${researchId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'pong') return;
            handleAgentEvent(data);
        } catch (e) {
            console.warn('Failed to parse message:', e);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket closed');
    };

    // Keep alive
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 15000);
}


// ─── Handle Agent Events ────────────────────────

function handleAgentEvent(event) {
    // Update pipeline
    if (event.event_type === 'pipeline_status' && event.metadata?.status) {
        updatePipeline(event.metadata.status);
    }

    // Update agent card
    updateAgentCard(event.agent, event.title);

    // Add to feed
    addEventToFeed(event);

    // Handle completion
    if (event.event_type === 'complete') {
        handleResearchComplete(event);
    }

    // Handle errors
    if (event.event_type === 'error') {
        updateStatusBadge('Error', 'red');
    }
}


// ─── Pipeline Progress ─────────────────────────

function updatePipeline(status) {
    // Mark previous steps as completed
    const statusIndex = PIPELINE_STEPS.indexOf(status);

    PIPELINE_STEPS.forEach((step, index) => {
        const el = document.getElementById(`step-${step}`);
        const connectors = document.querySelectorAll('.pipeline-connector');

        if (index < statusIndex) {
            // Completed
            el.classList.remove('active');
            el.classList.add('completed');
            if (connectors[index]) connectors[index].classList.add('active');
        } else if (index === statusIndex) {
            // Active
            el.classList.remove('completed');
            el.classList.add('active');
        } else {
            // Pending
            el.classList.remove('active', 'completed');
        }
    });

    // Mark completed
    if (status === 'completed') {
        PIPELINE_STEPS.forEach((step, index) => {
            const el = document.getElementById(`step-${step}`);
            el.classList.remove('active');
            el.classList.add('completed');
            const connectors = document.querySelectorAll('.pipeline-connector');
            if (connectors[index]) connectors[index].classList.add('active');
        });
    }

    currentStep = status;
}


// ─── Agent Cards ────────────────────────────────

function updateAgentCard(agentName, status) {
    // Deactivate all
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.remove('active');
    });

    // Activate current
    const card = document.getElementById(`agent-${agentName}`);
    if (card) {
        card.classList.add('active');
    }
}


// ─── Event Feed ─────────────────────────────────

function addEventToFeed(event) {
    const feed = document.getElementById('event-feed');

    // Remove empty state
    const emptyState = feed.querySelector('.feed-empty');
    if (emptyState) emptyState.remove();

    // Create event item
    const item = document.createElement('div');
    item.className = 'event-item';
    item.setAttribute('data-agent', event.agent);

    const time = new Date(event.timestamp).toLocaleTimeString();
    const icon = AGENT_ICONS[event.agent] || '🤖';

    item.innerHTML = `
        <div class="event-header">
            <span class="event-agent" style="color: ${AGENT_COLORS[event.agent] || '#fff'}">
                ${icon} ${event.agent.replace('_', ' ')}
            </span>
            <span class="event-time">${time}</span>
        </div>
        <div class="event-title">${escapeHtml(event.title)}</div>
        <div class="event-content">${escapeHtml(event.content)}</div>
    `;

    feed.appendChild(item);
    eventCount++;

    // Auto-scroll
    feed.scrollTop = feed.scrollHeight;
}


// ─── Research Complete ─────────────────────────

function handleResearchComplete(event) {
    updateStatusBadge('Complete', 'green');

    // Show results section
    const results = document.getElementById('results-section');
    results.style.display = 'block';

    // Close WebSocket
    if (ws) {
        ws.close();
        ws = null;
    }
}


// ─── View Report ────────────────────────────────

async function viewReport() {
    if (!currentResearchId) return;

    // Open report in new tab
    window.open(`/api/report/${currentResearchId}`, '_blank');
}


// ─── New Research ───────────────────────────────

function newResearch() {
    // Reset state
    currentResearchId = null;
    eventCount = 0;
    completedSteps = new Set();
    currentStep = null;

    if (ws) {
        ws.close();
        ws = null;
    }

    // Reset UI
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('input-section').style.display = 'block';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('topic-input').value = '';
    document.getElementById('custom-instructions').value = '';

    const btn = document.getElementById('btn-research');
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🚀</span><span class="btn-text">Start Research</span>';

    // Reset pipeline
    document.querySelectorAll('.pipeline-step').forEach(el => {
        el.classList.remove('active', 'completed');
    });
    document.querySelectorAll('.pipeline-connector').forEach(el => {
        el.classList.remove('active');
    });

    // Reset agent cards
    document.querySelectorAll('.agent-card').forEach(card => {
        card.classList.remove('active');
    });

    // Reset feed
    document.getElementById('event-feed').innerHTML = `
        <div class="feed-empty">
            <div class="feed-empty-icon">📡</div>
            <p>Waiting for agent activity...</p>
        </div>
    `;

    updateStatusBadge('Ready', 'green');
}


// ─── UI Helpers ─────────────────────────────────

function showDashboard() {
    document.getElementById('input-section').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
}

function updateStatusBadge(text, color) {
    const badge = document.getElementById('status-badge');
    const colors = {
        green:  { bg: 'rgba(74, 222, 128, 0.1)', fg: '#4ade80', border: 'rgba(74, 222, 128, 0.25)' },
        yellow: { bg: 'rgba(251, 191, 36, 0.1)', fg: '#fbbf24', border: 'rgba(251, 191, 36, 0.25)' },
        red:    { bg: 'rgba(248, 113, 113, 0.1)', fg: '#f87171', border: 'rgba(248, 113, 113, 0.25)' },
    };

    const c = colors[color] || colors.green;
    badge.style.background = c.bg;
    badge.style.color = c.fg;
    badge.style.borderColor = c.border;
    badge.textContent = `● ${text}`;
}

function setTopic(el) {
    document.getElementById('topic-input').value = el.textContent;
    document.getElementById('topic-input').focus();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ─── Keyboard Shortcut ─────────────────────────

document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        const input = document.getElementById('topic-input');
        if (document.activeElement === input) {
            e.preventDefault();
            startResearch();
        }
    }
});
