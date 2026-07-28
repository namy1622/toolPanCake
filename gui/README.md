# 📟 Pancake Control - Desktop GUI (CustomTkinter)

Phiên bản giao diện Desktop thay thế cho bản Web Dashboard (frontend + backend FastAPI).  
Được xây dựng bằng **Python CustomTkinter** với giao diện Dark Mode hiện đại.

---

## 📋 Tổng quan

Ứng dụng này **thay thế hoàn toàn** vai trò của:
- `frontend/` (HTML/CSS/JS) → Giao diện giờ là Python GUI
- `backend/main.py` (FastAPI Web Server) → GUI gọi trực tiếp script, không cần web server

Các file logic nghiệp vụ trong `scripts/` được **giữ nguyên 100%**, không sửa đổi.

---

## 🏗️ Các bước đã thực hiện

### Bước 1: Phân tích giao diện Web hiện tại
- Đọc file `frontend/index.html` (348 dòng) để hiểu toàn bộ cấu trúc giao diện gồm 5 phân khu:
  1. **Header** (Top bar): Logo, chọn trang Pancake, chọn ngày, nút Chạy/Dừng
  2. **File Browser** (Panel trái): Danh sách file JSON cào về
  3. **Data Explorer** (Panel giữa): Bảng CSV kết quả trích xuất AI
  4. **Chat Detail** (Panel phải): Bong bóng hội thoại & lập luận AI
  5. **Log Drawer** (Panel đáy): Terminal logs thời gian thực với 3 tab

### Bước 2: Phân tích Backend để xác định phần nào cần/không cần
- Đọc file `backend/main.py` (535 dòng) để hiểu:
  - Cách gọi script (`subprocess` chạy `scripts/*.py`)
  - Cách đọc dữ liệu (quét thư mục `data/`, đọc CSV `output/`)
  - Cách truyền log (WebSocket broadcast)
  - Cách đọc cấu hình (`appsettings.json`)
- **Kết luận**: GUI mới sẽ gọi trực tiếp các hàm tương đương, bỏ qua lớp Web Server.

### Bước 3: Phân tích Scripts để hiểu tham số đầu vào
- Đọc `scripts/scrape_pancake.py` → Nhận tham số: `[page_choice]` `[date]`
- Đọc `scripts/extract_ai_cot.py` → Nhận tham số: `[page]` `[model]` `[date]`
- Đọc `scripts/uncheck_kiem_hang.py` → Nhận tham số: `[page]`

### Bước 4: Cài đặt thư viện
```bash
pip install customtkinter tkcalendar
```
- `customtkinter` → Framework GUI Dark Mode hiện đại
- `tkcalendar` → Widget chọn ngày (DateEntry)

### Bước 5: Tạo cấu trúc thư mục `gui/`
```
gui/
├── __init__.py
├── app.py                         # Cửa sổ chính (Main Window)
├── components/
│   ├── __init__.py
│   ├── header_frame.py            # Thanh điều khiển trên cùng
│   ├── file_browser_frame.py      # Panel trái - danh sách file JSON
│   ├── data_explorer_frame.py     # Panel giữa - bảng CSV + dropdown Model AI
│   ├── chat_detail_frame.py       # Panel phải - bong bóng chat & AI reasoning
│   └── log_drawer_frame.py        # Panel đáy - terminal logs 3 tab
└── utils/
    ├── __init__.py
    ├── data_manager.py            # Đọc file JSON/CSV/appsettings.json
    └── process_runner.py          # Chạy subprocess script Python trong background thread
```

### Bước 6: Viết module tiện ích (`utils/`)

#### `data_manager.py`
- `get_workspace_dir()` → Tự xác định thư mục gốc dự án
- `load_appsettings()` → Đọc `appsettings.json` lấy danh sách Model AI
- `get_model_names()` → Trả về list tên model (VD: `API_Groq_GPT_120B`, `AI_Web`, ...)
- `get_json_files(page, date)` → Quét thư mục `data/{folder}/{date}/` lấy danh sách file `.json`
- `read_json_file(page, date, filename)` → Đọc nội dung 1 file JSON chat
- `read_csv_data(page, date)` → Đọc file CSV output (bỏ qua dòng comment `#`)
- `get_output_folder_path(page)` → Trả về đường dẫn thư mục Excel output

#### `process_runner.py`
- **Class `ProcessRunner`**: Chạy 1 script Python con trong `threading.Thread`:
  - Dùng `subprocess.Popen` với `stdout=PIPE` để bắt log realtime
  - Gửi từng dòng log qua `log_callback` function về GUI
  - Hỗ trợ `stop()` → `taskkill /F /T /PID` trên Windows
- **Class `PipelineRunner`**: Chạy tuần tự nhiều script (pipeline):
  - `run_single()` → Chạy 1 script đơn lẻ
  - `run_all()` → Chạy chain: scrape → extract → uncheck
  - Tự động chuyển tab log khi chuyển bước

### Bước 7: Viết các Component giao diện (`components/`)

#### `header_frame.py` - Thanh Header
- Logo text "⬡ PANCAKE CONTROL" màu Cyan
- 2 nút chọn trang (`Dây Thìa Canh` / `Trà Đông Trùng`) với viền sáng khi active
- Widget `DateEntry` (tkcalendar) chọn ngày làm việc
- Nút "▶ Chạy Tất Cả" (xanh lá) và "⏹ Dừng" (đỏ)
- Method `set_running_state()` tự động enable/disable nút khi có task chạy

#### `file_browser_frame.py` - Panel Trái
- Widget `FileItem` tùy chỉnh cho mỗi file JSON (icon ✅/📄, tên, dung lượng KB)
- `CTkScrollableFrame` chứa danh sách file cuộn được
- Nút "⬇ Chạy Cào Dữ Liệu" gọi `scrape_pancake.py`
- Highlight file đang chọn (viền Cyan)

#### `data_explorer_frame.py` - Panel Giữa
- `CTkOptionMenu` dropdown chọn Model AI (đọc từ `appsettings.json`)
- Nút "▶ Chạy AI", "🔄 Làm mới", "📁 Thư mục Excel"
- `ttk.Treeview` bảng dữ liệu Dark Mode với các cột:
  Khách Hàng | SĐT | Địa Chỉ | Giá Chốt | Số Hộp | Tên SP | Hội thoại
- Custom style `Dark.Treeview` (nền đen, chữ xám sáng, heading Cyan)

#### `chat_detail_frame.py` - Panel Phải
- Widget `ChatBubble` tùy chỉnh: tin nhắn Shop (nền xanh dương, lùi phải) vs Khách (nền xám, lùi trái)
- Textbox hiển thị lập luận AI (readonly, nền đen)
- `CTkScrollableFrame` cuộn danh sách bong bóng chat

#### `log_drawer_frame.py` - Panel Đáy
- Thanh header thu gọn/mở rộng (nút ▼/▲)
- 3 tab: "Logs Cào Dữ Liệu" | "Logs Phân Tích AI" | "Logs Bỏ Tag"
- Widget `LogTerminalPane`: Textbox nền đen chữ xanh lá (JetBrains Mono)
  - Checkbox "Tự cuộn" (auto-scroll)
  - Nút "Xóa" log
- Stats inline: Đã quét / Bỏ tag / Bỏ qua
- Nút "✓ Chạy Bỏ Tag Kiểm Hàng"

### Bước 8: Viết Main Window (`app.py`)
- Khởi tạo `CTk()` window 1400x850, Dark Mode
- Dựng layout 3 hàng: Header | Workspace (3 cột) | Log Drawer
- Kết nối callback giữa các component:
  - Chọn trang/ngày → refresh file list + CSV
  - Chọn file JSON → hiển thị chat detail
  - Chọn hàng CSV → hiển thị chat + AI reasoning
  - Nút chạy → gọi `PipelineRunner` background thread → log realtime lên terminal
- Method `_safe_log()` dùng `self.after(0, ...)` để thread-safe update GUI từ background thread

### Bước 9: Tạo file khởi chạy
- Tạo `Run_GUI.bat` → `python gui/app.py`

### Bước 10: Kiểm tra chạy thử
- Chạy `python gui/app.py` → Ứng dụng mở thành công, không lỗi

### Bước 11: Chuyển logic Validation từ `extract.js` sang Python GUI
- Phân tích file `frontend/js/extract.js` (dòng 190-296) và `frontend/css/style.css` (dòng 1255-1293)
- Xác định **3 loại cảnh báo** hiển thị trên bảng CSV:
  1. **🟡 Vàng (`warning_empty`)**: Ô trống hoặc có giá trị "Chưa rõ" (tên, SĐT, địa chỉ, giá, số hộp)
  2. **🔴 Đỏ (`danger_mismatch`)**: Giá chốt không khớp số hộp theo bảng giá chuẩn
  3. **🟤 Nâu đỏ (`phone_flagged`)**: SĐT nằm trong danh sách bị cấm (`0971838082`)
- Bổ sung thêm **1 loại mới** (không có trong bản Web):
  4. **🟣 Tím (`phone_duplicate`)**: SĐT bị trùng lặp giữa các khách hàng
- **Bảng giá hợp lệ** (đồng bộ từ `extract.js` dòng 214-223):
  | Số hộp | Giá hợp lệ (VNĐ) |
  |:---:|:---|
  | 1 | 100.000, 110.000, 120.000, 1.100.000 |
  | 2 | 150.000, 160.000, 200.000 |
  | 4 | 240.000 |
  | 5 | 350.000, 380.000, 400.000, 3.800.000 |
  | 6 | 300.000, 320.000 |
  | 7 | 350.000, 400.000 |
  | 8 | 350.000, 400.000 |
  | 10 | 500.000 |
- ~~Sử dụng `ttk.Treeview` tag system~~ → Đã nâng cấp sang **Custom Table** (`CTkScrollableFrame` + `CTkLabel`) để tô màu **từng ô riêng lẻ** thay vì cả hàng
- Thêm icon cảnh báo inline (⚠, 🚫, 🔁) vào giá trị hiển thị trên ô bảng

### Bước 12: Thêm Auto-Refresh Realtime khi đang chạy Task
- Khi bấm Chạy (Cào/AI/Bỏ tag/Chạy tất cả), hệ thống tự động bật timer refresh mỗi **3 giây**
- File list JSON (panel trái) và bảng CSV (panel giữa) cập nhật **tới đâu hiện tới đó** thay vì chờ chạy xong mới load
- Timer tự dừng khi task hoàn tất
- Sử dụng `self.after(3000, callback)` của Tkinter (thread-safe, không block UI)

### Bước 13: Định dạng chiều rộng cố định các cột bảng CSV
- Đặt độ rộng cố định cho từng cột (`COLUMNS`: Khách Hàng 120px, SĐT 100px, Địa Chỉ 250px, Giá 85px, Số Hộp 55px, Tên SP 130px, File nguồn 160px)
- Sử dụng `pack_propagate(False)` và `ROW_HEIGHT = 30` để chiều cao và chiều rộng từng ô không bị tràn/xô lệch
- Tiêu đề cột (Header) và Nội dung (Body) được giữ thẳng hàng 100%, không bị xô lệch dữ liệu khi text quá dài.

### Bước 14: Tối ưu Incremental UI Updating (Cập nhật vi sai siêu mượt)
- Thay vì xóa và vẽ lại toàn bộ danh sách file/hàng CSV mỗi lần có dữ liệu mới (`destroy()` & `re-pack`), áp dụng thuật toán **Diffing/Incremental Update**:
  - **Hàng/File cũ:** Giữ nguyên widget hiện có, chỉ cập nhật lại nội dung label (`configure(text=...)`) và màu ô nếu có sự thay đổi.
  - **Hàng/File mới:** Chỉ tạo và nối (`pack`) duy nhất widget mới vào cuối danh sách.
- **Kết quả:** Loại bỏ hoàn toàn hiện tượng nháy màn hình, giật lag hay chậm chạp khi dữ liệu được load realtime.

---

## 🚀 Cách sử dụng

```bash
# Cách 1: Double-click file
Run_GUI.bat

# Cách 2: Chạy bằng lệnh
python gui/app.py
```

---

## 🔗 So sánh với bản Web

| Tiêu chí | Bản Web (cũ) | Bản Desktop GUI (mới) |
|:---|:---|:---|
| Khởi chạy | `Run_Dashboard.bat` → Mở trình duyệt | `Run_GUI.bat` → Mở cửa sổ Desktop |
| Phụ thuộc | FastAPI + Uvicorn + Trình duyệt | Chỉ cần Python + CustomTkinter |
| Truyền log | WebSocket qua mạng | Thread callback trực tiếp |
| Đọc dữ liệu | HTTP API (`/api/files`, `/api/csv`) | Đọc file trực tiếp từ ổ đĩa |
| Scripts | Giữ nguyên `scripts/*.py` | Giữ nguyên `scripts/*.py` |

---

## 📦 Thư viện cần cài

```bash
pip install customtkinter tkcalendar
```

Các thư viện khác (`playwright`, `openai`, ...) đã được cài sẵn từ trước cho `scripts/`.
