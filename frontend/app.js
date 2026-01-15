// RoomSignal - WiFi Analyzer Frontend

const API_BASE = '/api';

// DOM Elements
const elements = {
    refreshBtn: document.getElementById('refreshBtn'),
    lastUpdate: document.getElementById('lastUpdate'),
    summaryCard: document.getElementById('summaryCard'),
    summaryIcon: document.getElementById('summaryIcon'),
    summaryMessage: document.getElementById('summaryMessage'),
    summaryRecommendation: document.getElementById('summaryRecommendation'),
    currentSection: document.getElementById('currentSection'),
    currentConnection: document.getElementById('currentConnection'),
    networksSection: document.getElementById('networksSection'),
    networkCount: document.getElementById('networkCount'),
    networksList: document.getElementById('networksList'),
    loadingState: document.getElementById('loadingState'),
    errorState: document.getElementById('errorState'),
    errorMessage: document.getElementById('errorMessage'),
    initialState: document.getElementById('initialState')
};

// Scan networks
async function scanNetworks() {
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/scan`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        showError(`Failed to scan networks: ${error.message}`);
    }
}

// Show loading state
function showLoading() {
    elements.refreshBtn.disabled = true;
    elements.loadingState.classList.remove('hidden');
    elements.errorState.classList.add('hidden');
    elements.initialState.classList.add('hidden');
    elements.summaryCard.classList.add('hidden');
    elements.currentSection.classList.add('hidden');
    elements.networksSection.classList.add('hidden');
}

// Show error state
function showError(message) {
    elements.refreshBtn.disabled = false;
    elements.loadingState.classList.add('hidden');
    elements.errorState.classList.remove('hidden');
    elements.errorMessage.textContent = message;
}

// Display scan results
function displayResults(data) {
    elements.refreshBtn.disabled = false;
    elements.loadingState.classList.add('hidden');
    elements.initialState.classList.add('hidden');
    elements.errorState.classList.add('hidden');

    // Update timestamp
    const now = new Date();
    elements.lastUpdate.textContent = `Last updated: ${now.toLocaleTimeString()}`;

    // Display summary
    if (data.summary) {
        displaySummary(data.summary);
    }

    // Display current connection
    if (data.current) {
        displayCurrentConnection(data.current);
    } else {
        elements.currentSection.classList.add('hidden');
    }

    // Display available networks
    if (data.networks && data.networks.length > 0) {
        displayNetworks(data.networks, data.current?.ssid);
    } else {
        elements.networksSection.classList.add('hidden');
    }
}

// Display summary card
function displaySummary(summary) {
    elements.summaryCard.classList.remove('hidden', 'excellent', 'good', 'fair', 'poor');
    elements.summaryCard.classList.add(summary.status);

    const icons = {
        excellent: '&#9989;',  // Green checkmark
        good: '&#128077;',     // Thumbs up
        fair: '&#9888;',       // Warning
        poor: '&#10060;',      // Red X
        disconnected: '&#128268;' // Plug
    };

    elements.summaryIcon.innerHTML = icons[summary.status] || '&#128225;';
    elements.summaryMessage.textContent = summary.message;
    elements.summaryRecommendation.textContent = summary.recommendation;
}

// Display current connection
function displayCurrentConnection(current) {
    elements.currentSection.classList.remove('hidden');

    const signalClass = getSignalClass(current.signal_quality);
    const gradeClass = `grade-${current.score.grade.toLowerCase()}`;

    elements.currentConnection.innerHTML = `
        <div class="current-main">
            <div class="current-header">
                <span class="current-ssid">${escapeHtml(current.ssid)}</span>
                <span class="band-badge ${current.band === '5GHz' ? 'band-5ghz' : 'band-2ghz'}">
                    ${current.band}
                </span>
            </div>

            <div class="stat">
                <span class="stat-label">Signal Strength</span>
                <div class="signal-bar-container">
                    <div class="signal-bar">
                        <div class="signal-bar-fill ${signalClass}"
                             style="width: ${current.signal_percentage}%"></div>
                    </div>
                    <span class="stat-value">${current.rssi} dBm</span>
                </div>
            </div>

            <div class="current-stats">
                <div class="stat">
                    <span class="stat-label">Quality</span>
                    <span class="stat-value">${current.signal_quality}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Channel</span>
                    <span class="stat-value">${current.channel} (${current.band_width})</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Speed</span>
                    <span class="stat-value">${current.tx_rate} Mbps</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Latency</span>
                    <span class="stat-value">${formatLatency(current.latency)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">SNR</span>
                    <span class="stat-value">${current.snr} dB</span>
                </div>
                <div class="stat">
                    <span class="stat-label">PHY Mode</span>
                    <span class="stat-value">${formatPhyMode(current.phy_mode)}</span>
                </div>
            </div>
        </div>

        <div class="score-display">
            <div class="score-circle ${gradeClass}">
                ${current.score.grade}
            </div>
            <span class="score-label">${current.score.total}/100</span>
        </div>
    `;
}

// Display available networks
function displayNetworks(networks, currentSsid) {
    elements.networksSection.classList.remove('hidden');
    elements.networkCount.textContent = networks.length;

    // Filter out current network and sort by score
    const otherNetworks = networks.filter(n => n.ssid !== currentSsid);

    if (otherNetworks.length === 0) {
        elements.networksList.innerHTML = `
            <div class="card" style="text-align: center; color: var(--text-secondary);">
                No other networks found at this location
            </div>
        `;
        return;
    }

    elements.networksList.innerHTML = otherNetworks.map((network, index) => {
        const signalClass = getSignalClass(network.signal_quality);
        const gradeClass = `grade-${network.score.grade.toLowerCase()}`;
        const isRecommended = index === 0 && network.score.total >= 40;

        return `
            <div class="network-card ${isRecommended ? 'recommended' : ''}">
                <div class="network-info">
                    <div class="network-ssid">
                        ${isRecommended ? '&#11088; ' : ''}${escapeHtml(network.ssid)}
                    </div>
                    <div class="network-details">
                        <span class="band-badge ${network.band === '5GHz' ? 'band-5ghz' : 'band-2ghz'}">
                            ${network.band}
                        </span>
                        <span>Ch ${network.channel}</span>
                        <span>${network.band_width}</span>
                        <span>${formatPhyMode(network.phy_mode)}</span>
                    </div>
                </div>

                <div class="network-signal">
                    ${network.rssi !== null ? `
                        <div class="signal-bar" style="width: 60px;">
                            <div class="signal-bar-fill ${signalClass}"
                                 style="width: ${network.signal_percentage}%"></div>
                        </div>
                        <div style="font-size: 0.8rem; margin-top: 4px; color: var(--text-secondary);">
                            ${network.rssi} dBm
                        </div>
                    ` : `
                        <div style="font-size: 0.8rem; color: var(--text-secondary);">
                            Signal N/A
                        </div>
                    `}
                </div>

                <div class="network-score">
                    <div class="mini-score ${gradeClass}">
                        ${network.score.grade}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Helper functions
function getSignalClass(quality) {
    const classes = {
        'Excellent': 'signal-excellent',
        'Good': 'signal-good',
        'Fair': 'signal-fair',
        'Poor': 'signal-poor'
    };
    return classes[quality] || 'signal-poor';
}

function formatLatency(latency) {
    if (!latency || latency.error) {
        return 'N/A';
    }
    return `${latency.avg_ms.toFixed(1)} ms`;
}

function formatPhyMode(phyMode) {
    if (!phyMode) return 'Unknown';

    // Convert 802.11ac to WiFi 5, etc.
    if (phyMode.includes('ax')) return 'WiFi 6';
    if (phyMode.includes('ac')) return 'WiFi 5';
    if (phyMode.includes('n')) return 'WiFi 4';
    if (phyMode.includes('g')) return 'WiFi 3';
    return phyMode;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Keyboard shortcut
document.addEventListener('keydown', (e) => {
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
            scanNetworks();
        }
    }
});
