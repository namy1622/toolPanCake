// CENTRAL CORE CONTROLLER - app.js
import { initScrape } from './scrape.js';
import { initExtract } from './extract.js';
import { initUncheck } from './uncheck.js';

// Global Application State
export const globalState = {
    selectedPage: "1",
    selectedDate: "",
    socket: null,
    isRunning: false,
    currentTask: null,          // "scrape", "extract", "uncheck", "run_all" or null
    activeTaskInChain: null,    // for run_all chain tracking ("scrape", "extract", "uncheck")
    config: {
        pages: [],
        models: []
    }
};

// WebSocket Message Listeners Registry
const wsListeners = [];

export function registerWsListener(callback) {
    wsListeners.push(callback);
}

// Format date to dd.MM.yy (Pancake visual format)
export function getTodayStr() {
    const now = new Date();
    const dd = String(now.getDate()).padStart(2, '0');
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const yy = String(now.getFullYear()).slice(-2);
    return `${dd}.${mm}.${yy}`;
}

// Global State Change Listeners Registry
const stateChangeListeners = [];

export function registerStateChangeListener(callback) {
    stateChangeListeners.push(callback);
}

export function notifyStateChange(type) {
    stateChangeListeners.forEach(listener => listener(type, globalState));
}

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Setup flatpickr visual calendar picker (Vietnam locale, dd.mm.yy format)
    globalState.selectedDate = getTodayStr();
    flatpickr("#date-select", {
        dateFormat: "d.m.y",
        defaultDate: globalState.selectedDate,
        onChange: (selectedDates, dateStr) => {
            globalState.selectedDate = dateStr;
            notifyStateChange('dateChange');
        }
    });

    // 2. Load configs
    await loadConfig();

    // 3. Connect to Websockets
    connectWebSocket();

    // 4. Setup collapsible log drawer and console pane tabs
    setupLogDrawer();

    // 5. Initialize Sub-modules
    initScrape(globalState);
    initExtract(globalState);
    initUncheck(globalState);

    // 6. Setup Global Controls (Run all, stop, visual page cards)
    setupGlobalControls();
    
    // Initial fetch to load default datasets
    setTimeout(() => notifyStateChange('init'), 300);
});

// Load configs from appsettings.json
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error("Could not retrieve system configuration.");
        const data = await response.json();
        
        globalState.config = data;

        // Populate AI Models dropdown
        const modelSelect = document.getElementById('model-select');
        if (modelSelect) {
            modelSelect.innerHTML = '';
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                modelSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Config fetch failed:", e);
    }
}

// WebSocket Connection Management
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
    
    const badge = document.getElementById('connection-badge');
    const badgeText = document.getElementById('status-text');

    badge.className = "connection-status badge-pending";
    badgeText.textContent = "Kết nối...";

    const socket = new WebSocket(wsUrl);
    globalState.socket = socket;

    socket.onopen = () => {
        badge.className = "connection-status badge-online";
        badgeText.textContent = "Online";
    };

    socket.onclose = () => {
        badge.className = "connection-status badge-offline";
        badgeText.textContent = "Offline";
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (err) => {
        console.error("WS error:", err);
        badge.className = "connection-status badge-offline";
        badgeText.textContent = "Lỗi kết nối";
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            
            // Sync status messages
            if (msg.type === 'status') {
                updateGlobalState(msg);
            }
            
            // Dispatch message to module listeners
            wsListeners.forEach(listener => listener(msg));
        } catch (e) {
            console.error("Error parsing message:", e);
        }
    };
}

// Update running indicators and block user controls during execution
function updateGlobalState(statusMsg) {
    globalState.currentTask = statusMsg.current_task;
    globalState.activeTaskInChain = statusMsg.active_task_in_chain;
    globalState.isRunning = statusMsg.status === 'running';

    const btnRunAll = document.getElementById('btn-run-all');
    const btnStop = document.getElementById('btn-stop');
    const dateInput = document.getElementById('date-select');
    const pageCards = document.querySelectorAll('.page-card');
    
    const btnScrape = document.getElementById('btn-run-scrape');
    const btnExtract = document.getElementById('btn-run-extract');
    const btnUncheck = document.getElementById('btn-run-uncheck');

    if (globalState.isRunning) {
        btnRunAll.disabled = true;
        btnStop.disabled = false;
        dateInput.disabled = true;
        pageCards.forEach(c => c.style.pointerEvents = 'none');
        
        if (btnScrape) btnScrape.disabled = true;
        if (btnExtract) btnExtract.disabled = true;
        if (btnUncheck) btnUncheck.disabled = true;
        
        // Expand bottom log drawer automatically to show logs if it's collapsed
        const logDrawer = document.getElementById('log-drawer');
        if (logDrawer && logDrawer.classList.contains('collapsed')) {
            toggleDrawer(logDrawer);
        }
        
        // Dynamic terminal tab activation based on current active task
        const runningTask = globalState.currentTask === 'run_all' ? globalState.activeTaskInChain : globalState.currentTask;
        activateTerminalTab(runningTask);

    } else {
        btnRunAll.disabled = false;
        btnStop.disabled = true;
        dateInput.disabled = false;
        pageCards.forEach(c => c.style.pointerEvents = 'auto');
        
        if (btnScrape) btnScrape.disabled = false;
        if (btnExtract) btnExtract.disabled = false;
        if (btnUncheck) btnUncheck.disabled = false;
    }
}

// Activate corresponding tab in bottom drawer logs
function activateTerminalTab(task) {
    if (!task) return;
    let terminalId = "";
    if (task === 'scrape') terminalId = "terminal-scrape";
    else if (task === 'extract') terminalId = "terminal-extract";
    else if (task === 'uncheck') terminalId = "terminal-uncheck";
    
    const activeTab = document.querySelector(`.terminal-tab[data-terminal="${terminalId}"]`);
    const activePane = document.getElementById(terminalId);
    
    if (activeTab && activePane) {
        document.querySelectorAll('.terminal-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.terminal-pane').forEach(p => p.classList.remove('active'));
        
        activeTab.classList.add('active');
        activePane.classList.add('active');
    }
}

// Collapsible Console Log Drawer Functions
function setupLogDrawer() {
    const logDrawer = document.getElementById('log-drawer');
    const toggleBtn = document.getElementById('btn-toggle-drawer');
    const toggleHeader = document.getElementById('log-drawer-toggle');

    // Toggle click handlers
    const handleToggle = () => toggleDrawer(logDrawer);
    toggleHeader.addEventListener('click', handleToggle);
    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        handleToggle();
    });

    // Console tabs inside drawer
    const terminalTabs = document.querySelectorAll('.terminal-tab');
    const terminalPanes = document.querySelectorAll('.terminal-pane');

    terminalTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent folding/unfolding when tab clicks
            const targetPaneId = tab.getAttribute('data-terminal');
            
            terminalTabs.forEach(t => t.classList.remove('active'));
            terminalPanes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const pane = document.getElementById(targetPaneId);
            if (pane) pane.classList.add('active');
        });
    });
}

function toggleDrawer(drawer) {
    const isCollapsed = drawer.classList.toggle('collapsed');
    const workspaceLayout = document.querySelector('.workspace-layout');
    if (isCollapsed) {
        workspaceLayout.style.marginBottom = "50px";
    } else {
        workspaceLayout.style.marginBottom = "360px";
    }
}

// Global click listeners
function setupGlobalControls() {
    const btnRunAll = document.getElementById('btn-run-all');
    const btnStop = document.getElementById('btn-stop');
    
    // Page Card selectable triggers
    const pageCards = document.querySelectorAll('.page-card');
    pageCards.forEach(card => {
        card.addEventListener('click', () => {
            if (globalState.isRunning) return; // Prevent switching pages during execution
            
            pageCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            
            globalState.selectedPage = card.getAttribute('data-page');
            notifyStateChange('pageChange');
        });
    });

    // Run All
    btnRunAll.addEventListener('click', async () => {
        const modelSelect = document.getElementById('model-select');
        const selectedModel = modelSelect ? modelSelect.value : "";
        
        try {
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task: "run_all",
                    page: globalState.selectedPage,
                    model: selectedModel,
                    date: globalState.selectedDate
                })
            });
            if (!response.ok) {
                const err = await response.json();
                alert(err.detail || "Không thể khởi chạy quy trình.");
            }
        } catch (e) {
            console.error("Error starting run all:", e);
        }
    });

    // Stop Task
    btnStop.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
        } catch (e) {
            console.error("Error stopping task:", e);
        }
    });
}

// Show sleek space-navy toast notification with optional action button
export function showToast(message, actionLabel = null, onActionClick = null) {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let actionBtnHtml = '';
    if (actionLabel && onActionClick) {
        actionBtnHtml = `
            <button class="toast-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                <span>${actionLabel}</span>
            </button>
        `;
    }

    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-icon">✨</div>
            <div class="toast-text">${message}</div>
        </div>
        ${actionBtnHtml}
    `;
    
    if (actionLabel && onActionClick) {
        const btn = toast.querySelector('.toast-btn');
        btn.addEventListener('click', () => {
            onActionClick();
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        });
    }
    
    container.appendChild(toast);
    
    // Auto remove after 15 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 300);
        }
    }, 15000);
}

