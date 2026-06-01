// TAG UNCHECK MODULE - uncheck.js
import { registerWsListener, registerStateChangeListener } from './app.js';

let appState = null;

// Stats Counters
let uncheckedCount = 0;
let skippedCount = 0;
let totalScanned = 0;

export function initUncheck(state) {
    appState = state;

    // Wire up Uncheck actions
    setupUncheckUI();

    // Log WebSocket Listener
    registerWsListener((msg) => {
        if (msg.type === 'log' && (msg.task === 'uncheck' || msg.task === 'system')) {
            appendUncheckLog(msg.data);
            
            // Dynamic log scraper to feed inline stats badges
            parseLogsForStats(msg.data);
        }
    });

    // Reset counters when page or date changes
    registerStateChangeListener((type) => {
        if (type === 'pageChange' || type === 'dateChange' || type === 'init') {
            resetStats();
        }
    });
}

function setupUncheckUI() {
    const btnRun = document.getElementById('btn-run-uncheck');
    const btnClear = document.getElementById('btn-clear-uncheck-log');

    // Run uncheck script
    if (btnRun) {
        btnRun.addEventListener('click', async (e) => {
            e.stopPropagation(); // Avoid folding/unfolding bottom drawer when header button clicks
            
            resetStats();
            try {
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task: "uncheck",
                        page: appState.selectedPage,
                        date: appState.selectedDate
                    })
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    alert(err.detail || "Không thể khởi chạy bộ bỏ Tag.");
                }
            } catch (e) {
                console.error("Unchecker launch failed:", e);
            }
        });
    }

    // Clear logs
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            const terminal = document.getElementById('uncheck-log');
            terminal.innerHTML = '<div class="log-line system">Bảng log đã được xóa. Sẵn sàng...</div>';
        });
    }
}

// Append logs with custom styles
function appendUncheckLog(text) {
    const terminal = document.getElementById('uncheck-log');
    if (!terminal) return;

    const line = document.createElement('div');
    line.className = 'log-line';
    
    if (text.includes('✅') || text.toLowerCase().includes('bỏ tích')) {
        line.classList.add('success');
    } else if (text.includes('❌') || text.toLowerCase().includes('lỗi') || text.toLowerCase().includes('error')) {
        line.classList.add('error');
    } else if (text.includes('⏭️') || text.toLowerCase().includes('bỏ qua')) {
        line.classList.add('skip');
    } else if (text.includes('--- Chat thứ') || text.includes('HOÀN TẤT')) {
        line.classList.add('system');
    }

    line.textContent = text;
    terminal.appendChild(line);

    // Auto-scroll
    const autoscroll = document.getElementById('uncheck-autoscroll');
    if (autoscroll && autoscroll.checked) {
        terminal.scrollTop = terminal.scrollHeight;
    }
}

// Dynamic parser to extract stats from raw console logs
function parseLogsForStats(text) {
    // 1. Success counter: e.g. "✅ Đã BỎ TÍCH 'Kiểm hàng' thành công!"
    if (text.includes("Đã BỎ TÍCH 'Kiểm hàng' thành công")) {
        uncheckedCount++;
        const s = document.getElementById('stat-uncheck-success');
        if (s) s.textContent = uncheckedCount;
    }

    // 2. Skip counter: e.g. "⏭️ BỎ QUA"
    if (text.includes("BỎ QUA")) {
        skippedCount++;
        const s = document.getElementById('stat-uncheck-skip');
        if (s) s.textContent = skippedCount;
    }

    // 3. Scan counter: e.g. "--- Chat thứ 12:"
    const match = text.match(/--- Chat thứ (\d+):/i);
    if (match) {
        totalScanned = parseInt(match[1]);
        const s = document.getElementById('stat-uncheck-total');
        if (s) s.textContent = totalScanned;
    }
}

function resetStats() {
    uncheckedCount = 0;
    skippedCount = 0;
    totalScanned = 0;
    
    const s1 = document.getElementById('stat-uncheck-success');
    const s2 = document.getElementById('stat-uncheck-skip');
    const s3 = document.getElementById('stat-uncheck-total');
    
    if (s1) s1.textContent = "0";
    if (s2) s2.textContent = "0";
    if (s3) s3.textContent = "0";
}
