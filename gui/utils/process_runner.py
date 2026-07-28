"""
process_runner.py - Module quản lý chạy script Python con (subprocess) trong background thread.
Bắt log realtime từ stdout của script và gửi callback về GUI để hiển thị.
"""

import os
import subprocess
import sys
import threading
from typing import Callable, Optional


class ProcessRunner:
    """
    Quản lý chạy một tiến trình Python con trong background thread.
    Log từ stdout/stderr được gửi về qua callback function.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_script(
        self,
        script_name: str,
        args: list,
        log_callback: Callable[[str], None],
        on_finished: Callable[[int], None],
        workspace_dir: str = None,
    ):
        """
        Chạy một script Python trong thread nền.

        Args:
            script_name: Tên file script (vd: scrape_pancake.py)
            args: Danh sách tham số dòng lệnh cho script
            log_callback: Hàm nhận từng dòng log (str) để hiển thị lên GUI
            on_finished: Hàm gọi khi script kết thúc, nhận exit_code (int)
            workspace_dir: Thư mục gốc dự án
        """
        if self.is_running:
            log_callback("⚠️ Đã có tiến trình đang chạy. Vui lòng đợi hoặc dừng trước.")
            return

        if workspace_dir is None:
            # Xác định từ vị trí file hiện tại
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workspace_dir = os.path.dirname(os.path.dirname(current_dir))

        script_path = os.path.join(workspace_dir, "scripts", script_name)
        if not os.path.exists(script_path):
            log_callback(f"❌ Không tìm thấy script: {script_path}")
            on_finished(-1)
            return

        self._stop_requested = False

        def _worker():
            python_exe = sys.executable
            cmd = [python_exe, "-u", script_path] + args

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            log_callback(f"⚙️ Bắt đầu chạy: {script_name} {' '.join(args)}")

            try:
                self._process = subprocess.Popen(
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

                while True:
                    if self._stop_requested:
                        break
                    line = self._process.stdout.readline()
                    if not line:
                        break
                    text = line.rstrip('\r\n')
                    if text:
                        log_callback(text)

                self._process.wait()
                exit_code = self._process.returncode

                if self._stop_requested:
                    log_callback("⚠️ Tiến trình đã bị dừng bởi người dùng.")
                elif exit_code == 0:
                    log_callback(f"✅ Hoàn tất {script_name} thành công!")
                else:
                    log_callback(f"❌ {script_name} kết thúc với mã lỗi: {exit_code}")

                on_finished(exit_code)

            except Exception as e:
                log_callback(f"❌ Lỗi hệ thống khi chạy script: {e}")
                on_finished(-1)
            finally:
                self._process = None

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop(self):
        """Buộc dừng tiến trình đang chạy."""
        self._stop_requested = True
        if self._process:
            try:
                pid = self._process.pid
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True, text=True
                    )
                else:
                    self._process.terminate()
            except Exception as e:
                print(f"Lỗi khi dừng tiến trình: {e}")
            self._process = None


class PipelineRunner:
    """
    Quản lý chạy tuần tự nhiều script (pipeline: scrape -> extract -> uncheck).
    Hiển thị log cho từng bước qua callback riêng biệt.
    """

    def __init__(self):
        self._runner = ProcessRunner()
        self._stop_requested = False
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def stop(self):
        self._stop_requested = True
        self._runner.stop()

    def run_single(
        self,
        script_name: str,
        args: list,
        log_callback: Callable[[str], None],
        on_finished: Callable[[int], None],
        workspace_dir: str = None,
    ):
        """Chạy một script đơn lẻ."""
        self._is_running = True
        self._stop_requested = False

        def _on_done(code):
            self._is_running = False
            on_finished(code)

        self._runner.run_script(script_name, args, log_callback, _on_done, workspace_dir)

    def run_all(
        self,
        page: str,
        model: str,
        date: str,
        log_callbacks: dict,  # {"scrape": fn, "extract": fn, "uncheck": fn}
        on_step_change: Callable[[str], None],
        on_all_finished: Callable[[bool], None],
        workspace_dir: str = None,
    ):
        """
        Chạy pipeline tuần tự: scrape -> extract -> uncheck.

        Args:
            log_callbacks: Dict chứa callback log cho từng bước
            on_step_change: Gọi khi chuyển sang bước mới (nhận tên bước)
            on_all_finished: Gọi khi toàn bộ pipeline kết thúc (True=thành công, False=lỗi)
        """
        self._is_running = True
        self._stop_requested = False

        if workspace_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workspace_dir = os.path.dirname(os.path.dirname(current_dir))

        steps = [
            ("scrape_pancake.py", [page, date], "scrape"),
            ("extract_ai_cot.py", [page, model, date], "extract"),
            ("uncheck_kiem_hang.py", [page], "uncheck"),
        ]

        def _run_step(index):
            if self._stop_requested or index >= len(steps):
                self._is_running = False
                success = not self._stop_requested and index >= len(steps)
                on_all_finished(success)
                return

            script_name, args, step_name = steps[index]
            on_step_change(step_name)
            log_cb = log_callbacks.get(step_name, lambda x: None)

            def _on_step_done(code):
                if code == 0 and not self._stop_requested:
                    _run_step(index + 1)
                else:
                    self._is_running = False
                    on_all_finished(False)

            self._runner.run_script(script_name, args, log_cb, _on_step_done, workspace_dir)

        _run_step(0)
