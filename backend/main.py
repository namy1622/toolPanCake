import asyncio
import csv
import json
import os
import sys
import subprocess
from typing import List, Dict, Optional

# Đảm bảo luồng xuất nhập chuẩn luôn dùng UTF-8 trên Windows để không bị lỗi CP1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Pancake Sales Automation Dashboard")

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".js", ".css", ".html")) or request.url.path == "/":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Tự động xác định thư mục gốc của dự án
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) == 'backend':
    WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
else:
    WORKSPACE_DIR = SCRIPT_DIR

# Mount frontend files
FRONTEND_DIR = os.path.join(WORKSPACE_DIR, "frontend")
os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(os.path.join(FRONTEND_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(FRONTEND_DIR, "js"), exist_ok=True)

# Mount static folders
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

# Pancake Pages Configuration (phải đồng bộ với scripts)
PAGES = {
    "1": {"name": "Dây Thìa Canh", "folder": "DayThiaCanh", "url": "https://pancake.vn/571938736002434"},
    "2": {"name": "Trà Đông Trùng", "folder": "TraDongTrung", "url": "https://pancake.vn/941461145712453"},
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class TaskState:
    def __init__(self):
        self.current_task: Optional[str] = None           # "scrape", "extract", "uncheck", "run_all"
        self.active_task_in_chain: Optional[str] = None   # "scrape", "extract", "uncheck" (for run_all tracking)
        self.status: str = "idle"                         # "idle", "running"
        self.active_process: Optional[asyncio.subprocess.Process] = None
        self.stop_requested: bool = False

state = TaskState()

class StartTaskRequest(BaseModel):
    task: str  # "scrape", "extract", "uncheck", "run_all"
    page: str  # "1" or "2"
    model: Optional[str] = None  # for extract
    date: Optional[str] = None   # selected date

class OpenFolderRequest(BaseModel):
    page: str

@app.get("/")
async def get_dashboard():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend entry file index.html not found.")

@app.get("/api/config")
async def get_config():
    settings = {}
    settings_file = os.path.join(WORKSPACE_DIR, "appsettings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception as e:
            print(f"Error loading appsettings.json: {e}")
            
    models = list(settings.keys())
    pages_list = [{"id": k, "name": v["name"], "folder": v["folder"], "url": v["url"]} for k, v in PAGES.items()]
    
    return {
        "pages": pages_list,
        "models": models
    }

@app.get("/api/files")
async def get_files(page: str, date: str):
    if page not in PAGES:
        raise HTTPException(status_code=400, detail="Invalid page choice")
    
    folder_name = PAGES[page]["folder"]
    dir_path = os.path.join(WORKSPACE_DIR, "data", folder_name, date)
    
    if not os.path.exists(dir_path):
        return []
    
    files = []
    try:
        for file in os.listdir(dir_path):
            if file.endswith(".json"):
                file_path = os.path.join(dir_path, file)
                size = os.path.getsize(file_path)
                files.append({
                    "name": file,
                    "size": size,
                    "is_processed": file.startswith("done_")
                })
        # Sắp xếp file theo index ở đầu tên (nếu có)
        def get_file_index(filename):
            match = re.match(r'^(?:done_)?(\d+)_', filename)
            return int(match.group(1)) if match else 999999
            
        import re
        files.sort(key=lambda x: get_file_index(x["name"]))
    except Exception as e:
        print(f"Error listing data files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    return files

@app.get("/api/file-content")
async def get_file_content(page: str, date: str, filename: str):
    if page not in PAGES:
        raise HTTPException(status_code=400, detail="Invalid page choice")
    
    folder_name = PAGES[page]["folder"]
    file_path = os.path.join(WORKSPACE_DIR, "data", folder_name, date, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/csv")
async def get_csv(page: str, date: str):
    if page not in PAGES:
        raise HTTPException(status_code=400, detail="Invalid page choice")
        
    folder_name = PAGES[page]["folder"]
    csv_path = os.path.join(WORKSPACE_DIR, "output", folder_name, f"{date}.csv")
    
    if not os.path.exists(csv_path):
        return []
        
    results = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Lọc bỏ các dòng comment bắt đầu bằng '#'
            reader = csv.DictReader(line for line in f if not line.startswith('#'))
            for row in reader:
                results.append({
                    "source_file": row.get("File Nguồn", ""),
                    "name": row.get("Tên Khách Hàng", ""),
                    "phone": row.get("Số Điện Thoại", ""),
                    "address": row.get("Địa Chỉ", ""),
                    "province": row.get("Tỉnh/Thành", ""),
                    "district": row.get("Quận/Huyện", ""),
                    "ward": row.get("Phường/Xã", ""),
                    "price": row.get("Giá Chốt", ""),
                    "quantity": row.get("Số Hộp", ""),
                    "reason": row.get("Lý Do Tính Số Hộp", row.get("Tổng Tin Nhắn", "")) # Backward compatibility
                })
    except Exception as e:
        print(f"Error reading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return results

@app.get("/api/chat-detail")
async def get_chat_detail(page: str, date: str, filename: str):
    if page not in PAGES:
        raise HTTPException(status_code=400, detail="Invalid page choice")
        
    folder_name = PAGES[page]["folder"]
    
    # Thử tìm trực tiếp
    path = os.path.join(WORKSPACE_DIR, "data", folder_name, date, filename)
    if not os.path.exists(path):
        # Thử tìm với hoặc không có prefix done_
        if filename.startswith("done_"):
            alt_filename = filename[5:]
        else:
            alt_filename = f"done_{filename}"
        path = os.path.join(WORKSPACE_DIR, "data", folder_name, date, alt_filename)
        
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File {filename} not found in workspace.")
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    return {
        "current_task": state.current_task,
        "active_task_in_chain": state.active_task_in_chain,
        "status": state.status
    }

@app.post("/api/start")
async def start_task(req: StartTaskRequest):
    if state.status == "running":
        raise HTTPException(status_code=400, detail="A task is already running.")
        
    print(f"[Server] Start task='{req.task}', page='{req.page}', model='{req.model}', date='{req.date}'", flush=True)
    
    state.current_task = req.task
    state.status = "running"
    state.stop_requested = False
    
    # Khởi chạy bất đồng bộ để trả về response ngay lập tức
    asyncio.create_task(run_task_pipeline(req.task, req.page, req.model, req.date))
    
    return {"message": f"Task {req.task} started successfully."}

@app.post("/api/open-folder")
async def open_folder(req: OpenFolderRequest):
    if req.page not in PAGES:
        raise HTTPException(status_code=400, detail="Invalid page choice")
        
    folder_name = PAGES[req.page]["folder"]
    folder_path = os.path.join(WORKSPACE_DIR, "output", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    try:
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])
        return {"message": "Folder opened successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_task():
    if state.status != "running":
        return {"message": "No task is currently running."}
        
    state.stop_requested = True
    await kill_active_process()
    
    state.status = "idle"
    state.current_task = None
    state.active_task_in_chain = None
    
    await manager.broadcast({
        "type": "status",
        "current_task": None,
        "active_task_in_chain": None,
        "status": "idle"
    })
    
    return {"message": "Task stop request sent."}

async def kill_active_process():
    if state.active_process:
        try:
            pid = state.active_process.pid
            # Trên Windows, dừng toàn bộ cây tiến trình (process tree) bằng taskkill
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, text=True)
            else:
                state.active_process.terminate()
            
            await manager.broadcast({
                "type": "log",
                "task": "system",
                "data": "⚠️ [Hệ thống] Đã buộc dừng tiến trình đang chạy thành công."
            })
        except Exception as e:
            print(f"Error terminating process: {e}")
            await manager.broadcast({
                "type": "log",
                "task": "system",
                "data": f"❌ [Hệ thống] Gặp lỗi khi cố dừng tiến trình: {e}"
            })
        state.active_process = None

def run_script_sync(cmd, log_task_name, workspace_dir, env, loop):
    try:
        # Khởi chạy tiến trình Python con đồng bộ sử dụng Popen tiêu chuẩn
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=workspace_dir,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        state.active_process = process
        
        # Đọc dữ liệu ra từ luồng stdout theo thời gian thực
        while True:
            line = process.stdout.readline()
            if not line:
                break
            text = line.rstrip('\r\n')
            
            # Gửi broadcast an toàn đa luồng quay lại vòng lặp sự kiện async
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "log",
                    "task": log_task_name,
                    "data": text
                }),
                loop
            )
            
        process.wait()
        exit_code = process.returncode
        state.active_process = None
        return exit_code
    except Exception as e:
        print(f"[Thread Error] Lỗi khi chạy tiến trình đồng bộ: {e}", flush=True)
        state.active_process = None
        return -1

async def run_single_script(script_name: str, args: List[str], log_task_name: str) -> bool:
    script_path = os.path.join(WORKSPACE_DIR, "scripts", script_name)
    if not os.path.exists(script_path):
        await manager.broadcast({
            "type": "log",
            "task": log_task_name,
            "data": f"❌ Lỗi: Không tìm thấy file script {script_name} tại {script_path}"
        })
        return False
        
    await manager.broadcast({
        "type": "log",
        "task": log_task_name,
        "data": f"⚙️ Đang bắt đầu tiến trình chạy script: {script_name} với tham số {args}..."
    })
    
    python_exe = sys.executable
    cmd = [python_exe, "-u", script_path] + args
    
    try:
        # Thiết lập PYTHONIOENCODING=utf-8 để ép các script con dùng UTF-8 trên Windows
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Lấy loop hiện tại của luồng chính
        loop = asyncio.get_running_loop()
        
        # Chạy tiến trình con đồng bộ trong ThreadPool của loop để tránh block event loop và Selector loop limits
        exit_code = await loop.run_in_executor(
            None,
            run_script_sync,
            cmd,
            log_task_name,
            WORKSPACE_DIR,
            env,
            loop
        )
        
        await manager.broadcast({
            "type": "log",
            "task": log_task_name,
            "data": f"ℹ️ Tiến trình kết thúc với mã thoát (Exit Code): {exit_code}"
        })
        
        return exit_code == 0
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[Server ERROR] {tb}", flush=True)
        await manager.broadcast({
            "type": "log",
            "task": log_task_name,
            "data": f"❌ Gặp lỗi hệ thống khi chạy script: {str(e)} ({type(e).__name__})"
        })
        state.active_process = None
        return False

async def run_task_pipeline(task: str, page: str, model: Optional[str], date: Optional[str]):
    try:
        # Chuẩn bị danh sách đối số
        scrape_args = [page]
        if date:
            scrape_args.append(date)
            
        model_arg = model if model else "1"
        extract_args = [page, model_arg]
        if date:
            extract_args.append(date)

        if task == "scrape":
            await manager.broadcast({"type": "status", "current_task": "scrape", "active_task_in_chain": "scrape", "status": "running"})
            success = await run_single_script("scrape_pancake.py", scrape_args, "scrape")
            
        elif task == "extract":
            await manager.broadcast({"type": "status", "current_task": "extract", "active_task_in_chain": "extract", "status": "running"})
            success = await run_single_script("extract_ai_cot.py", extract_args, "extract")
            
        elif task == "uncheck":
            await manager.broadcast({"type": "status", "current_task": "uncheck", "active_task_in_chain": "uncheck", "status": "running"})
            success = await run_single_script("uncheck_kiem_hang.py", [page], "uncheck")
            
        elif task == "run_all":
            await manager.broadcast({"type": "status", "current_task": "run_all", "active_task_in_chain": "scrape", "status": "running"})
            state.active_task_in_chain = "scrape"
            
            # 1. Scrape
            success = await run_single_script("scrape_pancake.py", scrape_args, "scrape")
            
            if success and not state.stop_requested:
                # 2. Extract
                state.active_task_in_chain = "extract"
                await manager.broadcast({"type": "status", "current_task": "run_all", "active_task_in_chain": "extract", "status": "running"})
                success = await run_single_script("extract_ai_cot.py", extract_args, "extract")
                
            if success and not state.stop_requested:
                # 3. Uncheck
                state.active_task_in_chain = "uncheck"
                await manager.broadcast({"type": "status", "current_task": "run_all", "active_task_in_chain": "uncheck", "status": "running"})
                success = await run_single_script("uncheck_kiem_hang.py", [page], "uncheck")
        else:
            success = False
            
        # Đánh dấu trạng thái hoàn thành
        if state.stop_requested:
            log_msg = "⚠️ Quy trình chạy đã bị dừng bởi người dùng."
        elif success:
            log_msg = "✅ Hoàn tất quy trình chạy thành công!"
        else:
            log_msg = "❌ Quy trình kết thúc nhưng có lỗi xảy ra ở một số bước."
            
        task_broad = state.active_task_in_chain if state.active_task_in_chain else task
        await manager.broadcast({
            "type": "log",
            "task": task_broad,
            "data": log_msg
        })
        
    except Exception as e:
        print(f"Error in running pipeline: {e}")
    finally:
        state.status = "idle"
        state.current_task = None
        state.active_task_in_chain = None
        
        await manager.broadcast({
            "type": "status",
            "current_task": None,
            "active_task_in_chain": None,
            "status": "idle"
        })

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Gửi cấu hình ban đầu qua socket
        await websocket.send_json({
            "type": "status",
            "current_task": state.current_task,
            "active_task_in_chain": state.active_task_in_chain,
            "status": state.status
        })
        while True:
            # Lắng nghe các tin nhắn từ client (nếu có, không thực sự cần)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    
    # Cổng chạy backend
    port = 8000
    
    # Tự động mở trình duyệt sau 1.5 giây
    def open_browser():
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception as e:
            print(f"Không thể mở trình duyệt tự động: {e}")
            
    # Lên lịch chạy mở trình duyệt nếu được gọi trực tiếp bằng Timer (an toàn với mọi phiên bản Python)
    import threading
    threading.Timer(1.5, open_browser).start()
    
    print(f"[Server] Dashboard Server starting at http://localhost:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, log_level="info", reload=True)
