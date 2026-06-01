// SCRAPE MODULE - scrape.js
import { registerWsListener, registerStateChangeListener } from './app.js';
import { viewChatDetail } from './extract.js'; // Cross-pane coordination

let appState = null;

export function initScrape(state) {
    appState = state;
    
    // Wire up Scrape Controls
    setupScrapeUI();
    
    // Log WebSocket Listener
    registerWsListener((msg) => {
        if (msg.type === 'log' && (msg.task === 'scrape' || msg.task === 'system')) {
            appendScrapeLog(msg.data);
            
            // Auto-reload file list when scraper creates a file or completes
            if (msg.data.includes("Đã lưu JSON tại") || msg.data.includes("HOÀN TẤT QUÉT")) {
                loadScrapedFiles();
            }
        }
    });

    // Re-fetch files when selections change
    registerStateChangeListener((type) => {
        if (type === 'pageChange' || type === 'dateChange' || type === 'init') {
            loadScrapedFiles();
        }
    });
}

function setupScrapeUI() {
    const btnRun = document.getElementById('btn-run-scrape');
    const btnClear = document.getElementById('btn-clear-scrape-log');

    // Run scraper script
    if (btnRun) {
        btnRun.addEventListener('click', async () => {
            try {
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task: "scrape",
                        page: appState.selectedPage,
                        date: appState.selectedDate
                    })
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    alert(err.detail || "Không thể khởi chạy Scraper.");
                }
            } catch (e) {
                console.error("Scraper launch failed:", e);
            }
        });
    }

    // Clear logs
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            const terminal = document.getElementById('scrape-log');
            terminal.innerHTML = '<div class="log-line system">Bảng log đã được xóa. Sẵn sàng...</div>';
        });
    }
}

// Append logs with custom severities
function appendScrapeLog(text) {
    const terminal = document.getElementById('scrape-log');
    if (!terminal) return;

    const line = document.createElement('div');
    line.className = 'log-line';
    
    if (text.includes('✅') || text.toLowerCase().includes('thành công')) {
        line.classList.add('success');
    } else if (text.includes('❌') || text.toLowerCase().includes('lỗi') || text.toLowerCase().includes('error')) {
        line.classList.add('error');
    } else if (text.includes('⚠️') || text.includes('[!]')) {
        line.classList.add('warning');
    } else if (text.includes('⏭️') || text.toLowerCase().includes('bỏ qua')) {
        line.classList.add('skip');
    } else if (text.includes('⚙️') || text.includes('=')) {
        line.classList.add('system');
    }

    line.textContent = text;
    terminal.appendChild(line);

    // Auto-scroll
    const autoscroll = document.getElementById('scrape-autoscroll');
    if (autoscroll && autoscroll.checked) {
        terminal.scrollTop = terminal.scrollHeight;
    }
}

// Fetch scraped JSON files
export async function loadScrapedFiles() {
    const fileListContainer = document.getElementById('scrape-file-list');
    const counter = document.getElementById('json-file-count');
    if (!fileListContainer) return;

    try {
        const response = await fetch(`/api/files?page=${appState.selectedPage}&date=${appState.selectedDate}`);
        if (!response.ok) throw new Error("Could not retrieve file browser dataset.");
        const files = await response.json();

        counter.textContent = `${files.length} files`;
        fileListContainer.innerHTML = '';

        if (files.length === 0) {
            fileListContainer.innerHTML = '<div class="empty-list-msg">Không có file dữ liệu nào cho ngày này. Hãy bấm "Chạy Cào Dữ Liệu" để thu thập.</div>';
            return;
        }

        files.forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.dataset.filename = file.name;

            const sizeKB = (file.size / 1024).toFixed(1);
            const isDone = file.is_processed;

            // Generate structured file browser node
            item.innerHTML = `
                <div class="file-info-col">
                    <span class="file-name-text" title="${file.name}">${file.name}</span>
                    <span class="file-size-text">${sizeKB} KB</span>
                </div>
                <span class="file-badge ${isDone ? 'done' : 'new'}">${isDone ? 'Đã xử lý' : 'Mới'}</span>
            `;

            item.addEventListener('click', () => {
                // Remove other active highlights and focus this file node
                document.querySelectorAll('.file-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                
                // Trực tiếp hiển thị bong bóng chat sang khung xem chi tiết ở cột bên phải
                // Đối với file chưa qua AI thì chưa có reasoning, hiển thị thông báo
                const cleanName = file.name.replace(/^done_/, '').replace(/^\d+_/, '').replace(/\.json$/, '');
                const reasoningPlaceholder = isDone 
                    ? "Nhấp vào dòng tương ứng trong bảng CSV để đọc lập luận tính số hộp chi tiết của AI."
                    : "Đoạn hội thoại này chưa được phân tích bằng AI. Hãy bấm nút 'Chạy Phân Tích AI' để thực hiện.";
                    
                viewChatDetail(file.name, cleanName, reasoningPlaceholder);
            });

            fileListContainer.appendChild(item);
        });
    } catch (e) {
        fileListContainer.innerHTML = `<div class="empty-list-msg text-red">Lỗi tải file: ${e.message}</div>`;
    }
}
