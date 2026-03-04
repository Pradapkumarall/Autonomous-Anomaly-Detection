/**
 * Autonomous Anomaly Detection Dashboard — Frontend Application
 * Handles data visualization, file uploads, SSE streaming, and UI interactions.
 */

// ══════════════════════════════════════════════════
// State
// ══════════════════════════════════════════════════
let allEvents = [];
let currentFilter = 'all';
let timelineChart = null;
let rootCauseChart = null;
let actionsChart = null;
let eventSource = null;
let isSimulating = false;

// ══════════════════════════════════════════════════
// Init
// ══════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initUploadZone();
    initCharts();
    loadExistingEvents();
    initScrollNav();
});

// ══════════════════════════════════════════════════
// API Helpers
// ══════════════════════════════════════════════════
async function api(url, options = {}) {
    try {
        const res = await fetch(url, options);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${url}`, e);
        return null;
    }
}

// ══════════════════════════════════════════════════
// Load Existing Events
// ══════════════════════════════════════════════════
async function loadExistingEvents() {
    const events = await api('/api/events');
    if (events && events.length > 0) {
        allEvents = events;
        renderAll();
    }
    refreshStats();
}

// ══════════════════════════════════════════════════
// Refresh Stats
// ══════════════════════════════════════════════════
async function refreshStats() {
    const stats = await api('/api/stats');
    if (!stats) return;

    animateValue('totalEvents', stats.total_events);
    animateValue('anomalyCount', stats.anomaly_count);
    animateValue('normalCount', stats.normal_count);
    document.getElementById('avgMTTR').textContent = stats.avg_mttr_ms.toFixed(1) + 'ms';
    document.getElementById('anomalyRate').textContent = stats.anomaly_rate.toFixed(1) + '%';

    // Update gauges with latest average values
    drawGauge('cpuGauge', stats.avg_cpu, 100, 'cpuValue', '%');
    drawGauge('memGauge', stats.avg_memory, 100, 'memValue', '%');
    drawGauge('latGauge', stats.avg_latency, 1500, 'latValue', 'ms');
    drawGauge('errGauge', stats.anomaly_rate, 100, 'errValue', '%');

    // Update distribution charts
    updateRootCauseChart(stats.root_causes);
    updateActionsChart(stats.actions_taken);
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    const current = parseInt(el.textContent) || 0;
    const diff = target - current;
    const steps = 20;
    let step = 0;

    const interval = setInterval(() => {
        step++;
        el.textContent = Math.round(current + (diff * step / steps));
        if (step >= steps) {
            el.textContent = target;
            clearInterval(interval);
        }
    }, 30);
}

// ══════════════════════════════════════════════════
// Gauges (Canvas)
// ══════════════════════════════════════════════════
function drawGauge(canvasId, value, max, labelId, unit) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(cx, cy) - 15;

    const pct = Math.min(value / max, 1);
    const startAngle = 0.75 * Math.PI;
    const endAngle = 2.25 * Math.PI;
    const valueAngle = startAngle + (endAngle - startAngle) * pct;

    // Determine color
    let color;
    if (canvasId === 'errGauge') {
        color = pct > 0.15 ? '#ef4444' : pct > 0.05 ? '#f59e0b' : '#10b981';
    } else if (canvasId === 'latGauge') {
        color = pct > 0.5 ? '#ef4444' : pct > 0.25 ? '#f59e0b' : '#10b981';
    } else {
        color = pct > 0.85 ? '#ef4444' : pct > 0.65 ? '#f59e0b' : '#10b981';
    }

    ctx.clearRect(0, 0, w, h);

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.lineWidth = 12;
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Value arc
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, valueAngle);
    ctx.lineWidth = 12;
    ctx.strokeStyle = color;
    ctx.lineCap = 'round';
    ctx.shadowColor = color;
    ctx.shadowBlur = 15;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Update label
    const label = document.getElementById(labelId);
    if (label) {
        if (unit === 'ms') {
            label.textContent = Math.round(value) + unit;
        } else {
            label.textContent = value.toFixed(1) + unit;
        }
        label.style.color = color;
    }
}

// ══════════════════════════════════════════════════
// Charts (Chart.js)
// ══════════════════════════════════════════════════
function initCharts() {
    const timeCtx = document.getElementById('timelineChart');
    if (!timeCtx) return;

    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
    Chart.defaults.font.family = "'Inter', sans-serif";

    timelineChart = new Chart(timeCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'CPU %',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: 'Memory %',
                    data: [],
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139,92,246,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: 'Anomaly',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239,68,68,0.15)',
                    fill: true,
                    tension: 0,
                    pointRadius: 4,
                    pointBackgroundColor: '#ef4444',
                    borderWidth: 0,
                    showLine: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 400 },
            interaction: { intersect: false, mode: 'index' },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: { maxTicksLimit: 15, font: { size: 10 } }
                },
                y: {
                    display: true,
                    min: 0,
                    max: 105,
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { font: { size: 10 } }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 20, font: { size: 11 } }
                }
            }
        }
    });

    // Root Cause Doughnut
    const rcCtx = document.getElementById('rootCauseChart');
    if (rcCtx) {
        rootCauseChart = new Chart(rcCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#10b981'],
                    borderWidth: 0,
                    hoverOffset: 8,
                }]
            },
            options: {
                responsive: true,
                cutout: '65%',
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true, font: { size: 11 } } }
                }
            }
        });
    }

    // Actions Doughnut
    const actCtx = document.getElementById('actionsChart');
    if (actCtx) {
        actionsChart = new Chart(actCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                    borderWidth: 0,
                    hoverOffset: 8,
                }]
            },
            options: {
                responsive: true,
                cutout: '65%',
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true, font: { size: 11 } } }
                }
            }
        });
    }
}

function updateTimelineChart(events) {
    if (!timelineChart) return;
    const last60 = events.slice(-60);

    timelineChart.data.labels = last60.map((e, i) => {
        const d = new Date(e.timestamp * 1000);
        return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    timelineChart.data.datasets[0].data = last60.map(e => e.cpu_usage || 0);
    timelineChart.data.datasets[1].data = last60.map(e => e.memory_usage || 0);
    timelineChart.data.datasets[2].data = last60.map(e => e.is_anomaly ? 100 : null);

    timelineChart.update('none');
}

function updateRootCauseChart(rootCauses) {
    if (!rootCauseChart || !rootCauses) return;
    const labels = Object.keys(rootCauses);
    const data = Object.values(rootCauses);

    rootCauseChart.data.labels = labels;
    rootCauseChart.data.datasets[0].data = data;
    rootCauseChart.update();
}

function updateActionsChart(actions) {
    if (!actionsChart || !actions) return;
    const mapping = {
        'auto_scale': 'Auto Scale',
        'restart_service': 'Restart Service',
        'block_transaction': 'Block Transaction',
        'none': 'No Action',
    };
    const labels = Object.keys(actions).map(k => mapping[k] || k);
    const data = Object.values(actions);

    actionsChart.data.labels = labels;
    actionsChart.data.datasets[0].data = data;
    actionsChart.update();
}

// ══════════════════════════════════════════════════
// Render All
// ══════════════════════════════════════════════════
function renderAll() {
    renderEvents();
    renderAgentLog();
    updateTimelineChart(allEvents);
    refreshStats();

    // Update latest gauges from last event
    if (allEvents.length > 0) {
        const last = allEvents[allEvents.length - 1];
        drawGauge('cpuGauge', last.cpu_usage || 0, 100, 'cpuValue', '%');
        drawGauge('memGauge', last.memory_usage || 0, 100, 'memValue', '%');
        drawGauge('latGauge', last.latency || 0, 1500, 'latValue', 'ms');
        drawGauge('errGauge', (last.error_rate || 0) * 100, 100, 'errValue', '%');
    }
}

// ══════════════════════════════════════════════════
// Event Cards
// ══════════════════════════════════════════════════
function renderEvents() {
    const container = document.getElementById('eventsList');
    if (!container) return;

    let filtered = allEvents;
    if (currentFilter === 'anomaly') {
        filtered = allEvents.filter(e => e.is_anomaly);
    } else if (currentFilter === 'normal') {
        filtered = allEvents.filter(e => !e.is_anomaly);
    }

    // Show last 50 events, newest first
    const display = filtered.slice(-50).reverse();

    if (display.length === 0) {
        container.innerHTML = `<div class="empty-state"><span class="empty-icon">📡</span><p>No events found.</p></div>`;
        return;
    }

    container.innerHTML = display.map(e => createEventCard(e)).join('');
}

function createEventCard(event) {
    const isAnomaly = event.is_anomaly;
    const confidence = (event.confidence || 0);

    let severity, icon, title;
    if (isAnomaly && confidence > 0.95) {
        severity = 'critical';
        icon = '🔴';
        title = event.root_cause || 'Critical Anomaly';
    } else if (isAnomaly) {
        severity = 'warning';
        icon = '🟡';
        title = event.root_cause || 'Warning Anomaly';
    } else {
        severity = 'normal';
        icon = '🟢';
        title = 'Normal Operation';
    }

    const ts = new Date(event.timestamp * 1000).toLocaleString();
    const action = event.selected_action ? event.selected_action.replace(/_/g, ' ') : '—';

    return `
        <div class="event-card severity-${severity}">
            <div class="event-severity">${icon}</div>
            <div class="event-info">
                <div class="event-title">${title}</div>
                <div class="event-meta">${ts} · ${event.processing_time_ms?.toFixed(1) || 0}ms · ${isAnomaly ? 'Action: ' + action : 'No action needed'}</div>
            </div>
            <div class="event-metrics">
                <div class="event-metric">
                    <span class="event-metric-value" style="color:${event.cpu_usage > 80 ? '#ef4444' : '#10b981'}">${event.cpu_usage?.toFixed(1) || 0}%</span>
                    <span class="event-metric-label">CPU</span>
                </div>
                <div class="event-metric">
                    <span class="event-metric-value" style="color:${event.memory_usage > 80 ? '#ef4444' : '#10b981'}">${event.memory_usage?.toFixed(1) || 0}%</span>
                    <span class="event-metric-label">MEM</span>
                </div>
                <div class="event-metric">
                    <span class="event-metric-value" style="color:${event.latency > 200 ? '#ef4444' : '#10b981'}">${event.latency?.toFixed(0) || 0}</span>
                    <span class="event-metric-label">LAT</span>
                </div>
                <div class="event-metric">
                    <span class="event-metric-value" style="color:${confidence > 0.5 ? '#ef4444' : '#10b981'}">${(confidence * 100).toFixed(1)}%</span>
                    <span class="event-metric-label">CONF</span>
                </div>
            </div>
        </div>`;
}

function filterEvents(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderEvents();
}

// ══════════════════════════════════════════════════
// Agent Activity Log
// ══════════════════════════════════════════════════
function renderAgentLog() {
    const container = document.getElementById('agentTimeline');
    if (!container) return;

    const anomalies = allEvents.filter(e => e.is_anomaly).slice(-20).reverse();

    if (anomalies.length === 0) {
        container.innerHTML = `<div class="empty-state"><span class="empty-icon">🧠</span><p>No agent actions recorded yet.</p></div>`;
        return;
    }

    container.innerHTML = anomalies.map(e => createAgentEntry(e)).join('');
}

function createAgentEntry(event) {
    const ts = new Date(event.timestamp * 1000).toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const conf = ((event.confidence || 0) * 100).toFixed(1);
    const actionLabel = event.selected_action ? event.selected_action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'None';
    const resultText = event.action_result || 'Completed';

    const isPending = resultText.toLowerCase().includes('pending');
    const dotClass = isPending ? 'dot-action' : 'dot-resolved';

    return `
        <div class="agent-entry">
            <div class="agent-dot-col">
                <div class="agent-dot dot-critical"></div>
                <div class="agent-line"></div>
            </div>
            <div class="agent-body">
                <div class="agent-header">
                    <span class="agent-tag tag-detect">DETECT</span>
                    <span class="agent-time">${ts}</span>
                </div>
                <div class="agent-message">
                    Anomaly detected with <strong>${conf}% confidence</strong>. 
                    CPU: ${event.cpu_usage?.toFixed(1)}% · Memory: ${event.memory_usage?.toFixed(1)}% · Latency: ${event.latency?.toFixed(0)}ms
                </div>
            </div>
        </div>
        <div class="agent-entry">
            <div class="agent-dot-col">
                <div class="agent-dot dot-action"></div>
                <div class="agent-line"></div>
            </div>
            <div class="agent-body">
                <div class="agent-header">
                    <span class="agent-tag tag-diagnose">DIAGNOSE</span>
                </div>
                <div class="agent-message">
                    Root cause identified: <strong>${event.root_cause || 'Unknown'}</strong>. 
                    Recommended action: <strong>${actionLabel}</strong>.
                </div>
            </div>
        </div>
        <div class="agent-entry">
            <div class="agent-dot-col">
                <div class="agent-dot ${dotClass}"></div>
                <div class="agent-line"></div>
            </div>
            <div class="agent-body">
                <div class="agent-header">
                    <span class="agent-tag ${isPending ? 'tag-action' : 'tag-resolved'}">${isPending ? 'PENDING' : 'RESOLVED'}</span>
                    <span class="agent-time">${event.processing_time_ms?.toFixed(1)}ms</span>
                </div>
                <div class="agent-message">${resultText}</div>
            </div>
        </div>`;
}

// ══════════════════════════════════════════════════
// File Upload
// ══════════════════════════════════════════════════
function initUploadZone() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            uploadFile(input.files[0]);
        }
    });
}

async function uploadFile(file) {
    const progress = document.getElementById('uploadProgress');
    const fill = document.getElementById('progressFill');
    const text = document.getElementById('progressText');
    const results = document.getElementById('uploadResults');

    progress.style.display = 'block';
    results.style.display = 'none';
    fill.style.width = '30%';
    text.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    fill.style.width = '60%';
    text.textContent = 'Running anomaly detection on dataset...';

    try {
        const res = await fetch('/api/upload-dataset', {
            method: 'POST',
            body: formData,
        });

        fill.style.width = '90%';

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const data = await res.json();
        fill.style.width = '100%';
        text.textContent = 'Analysis complete!';

        // Show results
        setTimeout(() => {
            progress.style.display = 'none';
            displayUploadResults(data);
        }, 500);

        // Reload events
        allEvents = await api('/api/events') || [];
        renderAll();

    } catch (err) {
        fill.style.width = '100%';
        fill.style.background = '#ef4444';
        text.textContent = `Error: ${err.message}`;
    }
}

function displayUploadResults(data) {
    const results = document.getElementById('uploadResults');
    const cards = document.getElementById('resultCards');
    const title = document.getElementById('resultTitle');
    const total = document.getElementById('resultTotal');
    const anomalies = document.getElementById('resultAnomalies');

    results.style.display = 'block';
    title.textContent = `Analysis Complete — ${data.filename}`;
    total.textContent = `${data.total_rows} rows`;
    anomalies.textContent = `${data.anomalies_detected} anomalies`;

    cards.innerHTML = data.results.map(r => createEventCard(r)).join('');
}

// ══════════════════════════════════════════════════
// Simulation
// ══════════════════════════════════════════════════
async function startSimulation() {
    const res = await api('/api/simulate/start', { method: 'POST' });
    if (!res) return;

    isSimulating = true;
    document.getElementById('btnStartSim').style.display = 'none';
    document.getElementById('btnStopSim').style.display = 'inline-flex';
    document.getElementById('simStatusDot').classList.add('active');
    document.getElementById('simStatusText').textContent = 'Live';

    // Connect SSE
    connectSSE();
}

async function stopSimulation() {
    await api('/api/simulate/stop', { method: 'POST' });
    isSimulating = false;
    document.getElementById('btnStartSim').style.display = 'inline-flex';
    document.getElementById('btnStopSim').style.display = 'none';
    document.getElementById('simStatusDot').classList.remove('active');
    document.getElementById('simStatusText').textContent = 'Idle';

    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}

function connectSSE() {
    if (eventSource) eventSource.close();

    eventSource = new EventSource('/api/stream');

    eventSource.onmessage = (e) => {
        try {
            const event = JSON.parse(e.data);
            if (event.type === 'heartbeat') return;

            allEvents.push(event);
            renderAll();
        } catch (err) {
            console.error('SSE parse error', err);
        }
    };

    eventSource.onerror = () => {
        // Reconnect after 2 seconds
        setTimeout(() => {
            if (isSimulating) connectSSE();
        }, 2000);
    };
}

// ══════════════════════════════════════════════════
// Clear Events
// ══════════════════════════════════════════════════
async function clearEvents() {
    await api('/api/clear-events', { method: 'POST' });
    allEvents = [];
    renderAll();

    // Reset timeline chart
    if (timelineChart) {
        timelineChart.data.labels = [];
        timelineChart.data.datasets.forEach(ds => ds.data = []);
        timelineChart.update();
    }

    // Reset distribution charts
    if (rootCauseChart) {
        rootCauseChart.data.labels = [];
        rootCauseChart.data.datasets[0].data = [];
        rootCauseChart.update();
    }

    if (actionsChart) {
        actionsChart.data.labels = [];
        actionsChart.data.datasets[0].data = [];
        actionsChart.update();
    }
}

// ══════════════════════════════════════════════════
// Scroll Navigation
// ══════════════════════════════════════════════════
function initScrollNav() {
    const links = document.querySelectorAll('.nav-link[data-section]');
    const sections = {};

    links.forEach(link => {
        const id = link.dataset.section;
        sections[id] = document.getElementById(id);
    });

    window.addEventListener('scroll', () => {
        let currentSection = '';
        const scrollPos = window.scrollY + 100;

        for (const [id, section] of Object.entries(sections)) {
            if (section && section.offsetTop <= scrollPos) {
                currentSection = id;
            }
        }

        links.forEach(link => {
            link.classList.toggle('active', link.dataset.section === currentSection);
        });
    });
}
