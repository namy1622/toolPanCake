// AI EXTRACT MODULE - extract.js
import { registerWsListener, registerStateChangeListener, showToast } from './app.js';
import { loadScrapedFiles } from './scrape.js'; // sync file indicators

let appState = null;

export function initExtract(state) {
    appState = state;

    // Wire up Extract Controls
    setupExtractUI();

    // Log WebSocket Listener
    registerWsListener((msg) => {
        if (msg.type === 'log' && (msg.task === 'extract' || msg.task === 'system')) {
            appendExtractLog(msg.data);
            
            // Auto reload table when a new chat finishes analyzing (dùng toLowerCase để không phân biệt hoa thường)
            const logText = msg.data.toLowerCase();
            if (logText.includes("đã đổi tên thành") || logText.includes("hoàn tất") || logText.includes("phân tích file")) {
                loadCsvData();
                loadScrapedFiles(); // sync left pane
            }
            
            // Trigger beautiful completion notification toast and glowing folder button
            if (logText.includes("hoàn tất! toàn bộ thông tin đã được lưu")) {
                // Show floating sleek space-navy toast notification with direct folder opening action
                showToast(
                    `🎉 Phân tích AI hoàn thành! Dữ liệu ngày ${appState.selectedDate} đã được lọc và xuất ra file Excel thành công.`, 
                    "📂 Mở Thư Mục", 
                    () => openOutputFolder()
                );
                
                // Trigger glowing animation on the main header folder button
                const btnOpenFolder = document.getElementById('btn-open-folder');
                if (btnOpenFolder) {
                    btnOpenFolder.classList.add('pulse-glow-highlight');
                }
            }
        }
    });

    // Re-fetch CSV data when selections change
    registerStateChangeListener((type) => {
        if (type === 'pageChange' || type === 'dateChange' || type === 'init') {
            loadCsvData();
            clearDetails();
            
            // Reset folder button glow highlight on choice change
            const btnOpenFolder = document.getElementById('btn-open-folder');
            if (btnOpenFolder) {
                btnOpenFolder.classList.remove('pulse-glow-highlight');
            }
        }
    });
}

// Global helper to open output directory
async function openOutputFolder() {
    if (!appState) return;
    try {
        await fetch('/api/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                page: appState.selectedPage
            })
        });
    } catch (e) {
        console.error("Failed to open folder:", e);
    }
}

function setupExtractUI() {
    const btnRun = document.getElementById('btn-run-extract');
    const btnRefresh = document.getElementById('btn-refresh-csv');
    const btnClear = document.getElementById('btn-clear-extract-log');
    const btnOpenFolder = document.getElementById('btn-open-folder');

    // Open Output Folder containing CSV reports
    if (btnOpenFolder) {
        btnOpenFolder.addEventListener('click', async () => {
            // Remove pulsing highlight once clicked
            btnOpenFolder.classList.remove('pulse-glow-highlight');
            await openOutputFolder();
        });
    }

    // Run AI Extractor script
    if (btnRun) {
        btnRun.addEventListener('click', async () => {
            // Remove pulsing highlight on new run starting
            if (btnOpenFolder) {
                btnOpenFolder.classList.remove('pulse-glow-highlight');
            }
            
            const modelSelect = document.getElementById('model-select');
            const selectedModel = modelSelect ? modelSelect.value : "";
            
            try {
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task: "extract",
                        page: appState.selectedPage,
                        model: selectedModel,
                        date: appState.selectedDate
                    })
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    alert(err.detail || "Không thể khởi chạy phân tích AI.");
                }
            } catch (e) {
                console.error("AI Extractor launch failed:", e);
            }
        });
    }

    // Manual Refresh Table
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            loadCsvData();
        });
    }

    // Clear logs
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            const terminal = document.getElementById('extract-log');
            terminal.innerHTML = '<div class="log-line system">Bảng log đã được xóa. Sẵn sàng...</div>';
        });
    }
}

// Append logs with custom styles
function appendExtractLog(text) {
    const terminal = document.getElementById('extract-log');
    if (!terminal) return;

    const line = document.createElement('div');
    line.className = 'log-line';
    
    const isSuccess = text.includes('✅') || text.toLowerCase().includes('hoàn tất');
    
    if (isSuccess) {
        line.classList.add('success');
    } else if (text.includes('❌') || text.toLowerCase().includes('lỗi') || text.toLowerCase().includes('error')) {
        line.classList.add('error');
    } else if (text.includes('⚠️') || text.includes('[!]')) {
        line.classList.add('warning');
    } else if (text.includes('->') || text.includes('Phân tích file')) {
        line.classList.add('system');
    }

    // If it is the final completion log line, append a super convenient inline button inside the log terminal!
    if (text.toLowerCase().includes("hoàn tất! toàn bộ thông tin đã được lưu")) {
        line.textContent = text + " ";
        
        const inlineBtn = document.createElement('button');
        inlineBtn.className = 'inline-log-btn';
        inlineBtn.innerHTML = `
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align: middle; margin-right: 2px;">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <span>Mở thư mục Excel</span>
        `;
        inlineBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const btnOpenFolder = document.getElementById('btn-open-folder');
            if (btnOpenFolder) btnOpenFolder.classList.remove('pulse-glow-highlight');
            await openOutputFolder();
        });
        line.appendChild(inlineBtn);
    } else {
        line.textContent = text;
    }
    
    terminal.appendChild(line);

    // Auto-scroll
    const autoscroll = document.getElementById('extract-autoscroll');
    if (autoscroll && autoscroll.checked) {
        terminal.scrollTop = terminal.scrollHeight;
    }
}

// Helper to parse price string to number
function parsePrice(priceStr) {
    if (!priceStr) return 0;
    const clean = priceStr.toString().replace(/[^0-9]/g, '');
    const num = parseInt(clean);
    return isNaN(num) ? 0 : num;
}

// Helper to parse quantity string to integer box count
function parseQuantity(qtyStr) {
    if (!qtyStr) return null;
    const clean = qtyStr.toString().trim().toLowerCase();
    const match = clean.match(/(\d+)/);
    if (match) {
        return parseInt(match[1]);
    }
    return null;
}

// Helper to check if a Province/District/Ward value matches within the address string
function checkAddressMatch(address, fieldValue) {
    if (!fieldValue || fieldValue.trim() === '' || !address || address.trim() === '') return true;
    const normalize = s => s.toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // Remove Vietnamese diacritics
        .replace(/đ/g, 'd').replace(/Đ/g, 'D')
        .replace(/\s+/g, ' ').trim();
    const normalizedAddr = normalize(address);
    const normalizedField = normalize(fieldValue);
    // Try direct substring match
    if (normalizedAddr.includes(normalizedField)) return true;
    // Try matching individual significant words (skip common prefixes like tinh/huyen/xa/quan/phuong/thi xa/thanh pho)
    const prefixes = ['tinh', 'thanh pho', 'tp', 'quan', 'huyen', 'thi xa', 'tx', 'phuong', 'xa', 'thi tran', 'tt'];
    let cleanedField = normalizedField;
    for (const prefix of prefixes) {
        if (cleanedField.startsWith(prefix + ' ')) {
            cleanedField = cleanedField.slice(prefix.length).trim();
            break;
        }
    }
    if (cleanedField && normalizedAddr.includes(cleanedField)) return true;
    return false;
}

// Helper to validate price against quantity
function validatePriceAndQuantity(price, qty) {
    if (price === 0 || qty === null) return true; // Empty checks handle this
    
    // Correct price list for each box count
    const validMap = {
        1: [100000, 110000, 120000, 1100000],
        2: [150000, 160000, 200000],
        4: [240000],
        5: [350000, 380000, 400000, 3800000],
        6: [300000, 320000],
        7: [350000, 400000],
        8: [350000, 400000],
        10: [500000]
    };
    
    if (validMap[qty]) {
        return validMap[qty].includes(price);
    }
    return false;
}

// Fetch and load parsed CSV data table
async function loadCsvData() {
    const tbody = document.getElementById('extracted-customers-body');
    if (!tbody) return;

    try {
        const response = await fetch(`/api/csv?page=${appState.selectedPage}&date=${appState.selectedDate}`);
        if (!response.ok) throw new Error("Could not retrieve CSV dataset.");
        const data = await response.json();

        tbody.innerHTML = '';

        if (data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="table-placeholder">Chưa có dữ liệu trích xuất cho ngày làm việc này. Hãy bấm "Chạy Phân Tích AI" để bắt đầu lọc dữ liệu.</td>
                </tr>
            `;
            return;
        }

        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.dataset.source = row.source_file;
            
            // Format clean phone number
            let cleanPhone = row.phone ? row.phone.trim() : '';
            if (cleanPhone.startsWith("'")) {
                cleanPhone = cleanPhone.slice(1);
            }

            const parsedPrice = parsePrice(row.price);
            const parsedQty = parseQuantity(row.quantity);

            // Validation checks
            const isNameEmpty = !row.name || row.name.trim() === '' || row.name.trim() === 'Chưa rõ';
            const isPhoneEmpty = !cleanPhone || cleanPhone.trim() === '' || cleanPhone.trim() === 'Chưa rõ';
            const isAddressEmpty = !row.address || row.address.trim() === '' || row.address.trim() === 'Chưa rõ';
            const isPriceEmpty = !row.price || row.price.trim() === '' || row.price.trim() === 'Chưa rõ' || parsedPrice === 0;
            const isQtyEmpty = !row.quantity || row.quantity.trim() === '' || row.quantity.trim() === 'Chưa rõ' || row.quantity.trim() === '-' || parsedQty === null;

            // Price vs Quantity validation
            let hasMismatch = false;
            if (!isPriceEmpty && !isQtyEmpty) {
                hasMismatch = !validatePriceAndQuantity(parsedPrice, parsedQty);
            }

            // Cell styling classes
            const nameClass = isNameEmpty ? 'cell-warning-empty' : '';
            const phoneClass = isPhoneEmpty ? 'cell-warning-empty' : '';
            const addressClass = isAddressEmpty ? 'cell-warning-empty' : '';
            
            let priceClass = '';
            if (isPriceEmpty) {
                priceClass = 'cell-warning-empty';
            } else if (hasMismatch) {
                priceClass = 'cell-danger-mismatch';
            }

            let qtyClass = '';
            if (isQtyEmpty) {
                qtyClass = 'cell-warning-empty';
            } else if (hasMismatch) {
                qtyClass = 'cell-danger-mismatch';
            }

            // Đối chiếu Tỉnh/Huyện/Xã với chuỗi Địa Chỉ gốc
            const provinceMatch = checkAddressMatch(row.address, row.province);
            const districtMatch = checkAddressMatch(row.address, row.district);
            const wardMatch = checkAddressMatch(row.address, row.ward);

            const provinceClass = (!row.province || row.province.trim() === '') ? '' : (provinceMatch ? '' : 'cell-address-mismatch');
            const districtClass = (!row.district || row.district.trim() === '') ? '' : (districtMatch ? '' : 'cell-address-mismatch');
            const wardClass = (!row.ward || row.ward.trim() === '') ? '' : (wardMatch ? '' : 'cell-address-mismatch');

            tr.innerHTML = `
                <td class="${nameClass}"><strong>${row.name || 'Chưa rõ'}</strong></td>
                <td class="${phoneClass}"><span class="text-cyan">${cleanPhone || 'Chưa rõ'}</span></td>
                <td class="${addressClass}" title="${row.address}">${row.address || 'Chưa rõ'}</td>
                <td class="${provinceClass}">${row.province || ''}</td>
                <td class="${districtClass}">${row.district || ''}</td>
                <td class="${wardClass}">${row.ward || ''}</td>
                <td class="${priceClass}"><span class="text-green">${formatPrice(row.price)}đ</span></td>
                <td class="${qtyClass}"><span class="file-badge done">${row.quantity || '-'}</span></td>
                <td>
                    <button class="btn btn-xs btn-view-detail">Mở chat</button>
                </td>
            `;

            const selectRow = () => {
                document.querySelectorAll('#extracted-customers-body tr').forEach(r => r.classList.remove('active-row'));
                tr.classList.add('active-row');
                
                // Đồng bộ làm sáng file tương ứng bên Left File Browser nếu tìm thấy
                document.querySelectorAll('.file-item').forEach(item => {
                    if (item.getAttribute('data-filename') === row.source_file || 
                        item.getAttribute('data-filename') === `done_${row.source_file}`) {
                        item.classList.add('active');
                        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    } else {
                        item.classList.remove('active');
                    }
                });
                
                // Hiển thị bong bóng chat & Lập luận của AI
                viewChatDetail(row.source_file, row.name, row.reason);
            };

            // Double binding triggers
            tr.addEventListener('click', selectRow);
            tr.querySelector('.btn-view-detail').addEventListener('click', (e) => {
                e.stopPropagation();
                selectRow();
            });

            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="table-placeholder text-red">Lỗi tải dữ liệu CSV: ${e.message}</td>
            </tr>
        `;
    }
}

// EXPORTED: Display chat transcripts bubble viewer (Allows scrape.js to trigger it directly!)
export async function viewChatDetail(filename, customerName, aiReason) {
    const placeholder = document.getElementById('chat-detail-placeholder');
    const content = document.getElementById('chat-detail-content');
    
    const panelName = document.getElementById('detail-customer-name');
    const panelSource = document.getElementById('detail-source-file');
    const panelReasoning = document.getElementById('detail-ai-reasoning');
    const panelDialog = document.getElementById('detail-chat-dialog');

    if (placeholder) placeholder.style.display = 'none';
    if (content) content.classList.remove('hidden');

    panelName.textContent = customerName || "Khách Hàng";
    panelSource.textContent = filename || "";
    panelReasoning.textContent = aiReason || "Không có dữ liệu lập luận chi tiết.";
    panelDialog.innerHTML = '<div class="viewer-placeholder">Đang tải lịch sử hội thoại chat...</div>';

    try {
        const response = await fetch(`/api/chat-detail?page=${appState.selectedPage}&date=${appState.selectedDate}&filename=${filename}`);
        if (!response.ok) throw new Error("Could not fetch chat transcript details.");
        const data = await response.json();

        panelDialog.innerHTML = '';
        const messages = data.messages || [];

        if (messages.length === 0) {
            panelDialog.innerHTML = '<div class="viewer-placeholder">Hội thoại này không chứa tin nhắn nào.</div>';
            return;
        }

        messages.forEach(msg => {
            const bubble = document.createElement('div');
            
            const isSelf = msg.sender === 'Tôi';
            bubble.className = `chat-bubble ${isSelf ? 'self' : 'customer'}`;

            bubble.innerHTML = `
                <div class="bubble-sender">${msg.sender}</div>
                <div>${msg.content}</div>
            `;
            
            panelDialog.appendChild(bubble);
        });

        // Auto-scroll chat transcript container to bottom
        setTimeout(() => {
            panelDialog.scrollTop = panelDialog.scrollHeight;
        }, 100);

    } catch (e) {
        panelDialog.innerHTML = `<div class="viewer-placeholder text-red">Lỗi tải dữ liệu chat: ${e.message}</div>`;
    }
}

function clearDetails() {
    const placeholder = document.getElementById('chat-detail-placeholder');
    const content = document.getElementById('chat-detail-content');
    if (placeholder) placeholder.style.display = 'flex';
    if (content) content.classList.add('hidden');
}

// Format prices (e.g. 240000 -> 240.000)
function formatPrice(priceStr) {
    if (!priceStr) return '0';
    const num = parseInt(priceStr.replace(/[^0-9]/g, ''));
    if (isNaN(num)) return priceStr;
    return num.toLocaleString('vi-VN');
}
