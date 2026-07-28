"""
app.py - Cửa sổ ứng dụng chính Pancake Control Desktop GUI.
Kết nối tất cả các component lại và quản lý logic điều phối.
"""

import datetime
import os
import subprocess
import sys
import threading

import customtkinter as ctk

# Thêm thư mục cha vào sys.path để import các module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from gui.components.header_frame import HeaderFrame
from gui.components.file_browser_frame import FileBrowserFrame
from gui.components.data_explorer_frame import DataExplorerFrame
from gui.components.chat_detail_frame import ChatDetailFrame
from gui.components.log_drawer_frame import LogDrawerFrame
from gui.utils.data_manager import (
    get_model_names, get_json_files, read_json_file,
    read_csv_data, get_output_folder_path, PAGES
)
from gui.utils.process_runner import PipelineRunner


class PancakeControlApp(ctk.CTk):
    """Cửa sổ chính ứng dụng Pancake Control Desktop."""

    def __init__(self):
        super().__init__()

        # === Cấu hình cửa sổ ===
        self.title("Pancake Control - Hệ thống Điều phối & Phân tích Đơn hàng")
        self.geometry("1400x850")
        self.minsize(1100, 650)

        # Dark mode
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Đặt màu nền chính
        self.configure(fg_color="#0E1621")

        # State
        self._runner = PipelineRunner()
        self._current_page = "1"
        self._current_date = datetime.datetime.now().strftime("%d.%m.%y")
        self._auto_refresh_id = None  # ID timer auto-refresh khi task đang chạy

        # Layout chính
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self._load_initial_data()

    def _build_ui(self):
        """Dựng toàn bộ giao diện."""

        # === ROW 0: HEADER ===
        self._header = HeaderFrame(
            self,
            on_page_change=self._on_page_change,
            on_date_change=self._on_date_change,
            on_run_all=self._on_run_all,
            on_stop=self._on_stop,
            fg_color="#131A26",
        )
        self._header.grid(row=0, column=0, sticky="ew")

        # === ROW 1: WORKSPACE (3 panels) ===
        workspace = ctk.CTkFrame(self, fg_color="#0E1621", corner_radius=0)
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=0)   # File browser - chiều rộng cố định
        workspace.grid_columnconfigure(1, weight=1)   # Data explorer - co giãn
        workspace.grid_columnconfigure(2, weight=0)   # Chat detail - chiều rộng cố định

        # Panel Trái: File Browser
        self._file_browser = FileBrowserFrame(
            workspace,
            on_file_select=self._on_file_select,
            on_run_scrape=self._on_run_scrape,
            fg_color="#141D2B",
        )
        self._file_browser.grid(row=0, column=0, sticky="nsew")

        # Separator trái
        sep1 = ctk.CTkFrame(workspace, width=2, fg_color="#1A2332", corner_radius=0)
        sep1.grid(row=0, column=0, sticky="nse")

        # Panel Giữa: Data Explorer
        models = get_model_names()
        self._data_explorer = DataExplorerFrame(
            workspace,
            models=models,
            on_run_extract=self._on_run_extract,
            on_refresh=self._refresh_data,
            on_open_folder=self._on_open_folder,
            on_row_select=self._on_csv_row_select,
            fg_color="#111921",
        )
        self._data_explorer.grid(row=0, column=1, sticky="nsew")

        # Separator phải
        sep2 = ctk.CTkFrame(workspace, width=2, fg_color="#1A2332", corner_radius=0)
        sep2.grid(row=0, column=1, sticky="nse")

        # Panel Phải: Chat Detail
        self._chat_detail = ChatDetailFrame(
            workspace,
            fg_color="#111921",
        )
        self._chat_detail.grid(row=0, column=2, sticky="nsew")

        # === ROW 2: LOG DRAWER ===
        self._log_drawer = LogDrawerFrame(
            self,
            on_run_uncheck=self._on_run_uncheck,
            fg_color="#0D1117",
        )
        self._log_drawer.grid(row=2, column=0, sticky="ew")
        # Đặt chiều cao mặc định cho log drawer
        self._log_drawer.configure(height=250)

    def _load_initial_data(self):
        """Nạp dữ liệu ban đầu khi mở ứng dụng."""
        self._current_date = self._header.get_date_str()
        self._refresh_data()

    # ==========================================
    # EVENT HANDLERS
    # ==========================================

    def _on_page_change(self, page_id: str):
        """Khi người dùng chuyển trang Pancake."""
        self._current_page = page_id
        self._chat_detail.clear_detail()
        self._refresh_data()

    def _on_date_change(self, date_str: str):
        """Khi người dùng chọn ngày mới."""
        self._current_date = date_str
        self._chat_detail.clear_detail()
        self._refresh_data()

    def _refresh_data(self):
        """Tải lại danh sách file JSON và bảng CSV."""
        self._current_date = self._header.get_date_str()

        # Tải file JSON
        files = get_json_files(self._current_page, self._current_date)
        self._file_browser.load_files(files)

        # Tải CSV
        csv_data = read_csv_data(self._current_page, self._current_date)
        self._data_explorer.load_csv_data(csv_data)

    def _on_file_select(self, file_info: dict):
        """Khi người dùng chọn một file JSON trong file browser."""
        filename = file_info["name"]
        data = read_json_file(self._current_page, self._current_date, filename)
        if data:
            customer_name = data.get("customerName", "Unknown")
            messages = data.get("messages", [])
            ai_reasoning = data.get("ai_reasoning", "")
            self._chat_detail.show_chat_detail(
                customer_name=customer_name,
                source_file=filename,
                ai_reasoning=ai_reasoning,
                messages=messages,
            )

    def _on_csv_row_select(self, row_data: dict):
        """Khi người dùng chọn một hàng trong bảng CSV."""
        source_file = row_data.get("source_file", "")
        if source_file:
            data = read_json_file(self._current_page, self._current_date, source_file)
            if data:
                customer_name = data.get("customerName", row_data.get("name", "Unknown"))
                messages = data.get("messages", [])
                ai_reasoning = data.get("ai_reasoning", "")
                self._chat_detail.show_chat_detail(
                    customer_name=customer_name,
                    source_file=source_file,
                    ai_reasoning=ai_reasoning,
                    messages=messages,
                )
            else:
                # Nếu không tìm được file JSON, vẫn hiển thị thông tin từ CSV
                self._chat_detail.show_chat_detail(
                    customer_name=row_data.get("name", "Unknown"),
                    source_file=source_file,
                    ai_reasoning="Không tìm thấy file JSON gốc để đọc lập luận AI.",
                    messages=[],
                )

    def _on_open_folder(self):
        """Mở thư mục output/Excel."""
        folder_path = get_output_folder_path(self._current_page)
        if folder_path and os.path.exists(folder_path):
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])

    # ==========================================
    # TASK RUNNERS
    # ==========================================

    def _set_running_state(self, is_running: bool):
        """Cập nhật trạng thái UI khi có/không task đang chạy."""
        self._header.set_running_state(is_running)
        self._file_browser.set_scrape_enabled(not is_running)
        self._data_explorer.set_extract_enabled(not is_running)
        self._log_drawer.set_uncheck_enabled(not is_running)

        # Bật/tắt auto-refresh realtime
        if is_running:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _start_auto_refresh(self):
        """Bắt đầu auto-refresh file list + CSV mỗi 1 giây khi task đang chạy."""
        self._stop_auto_refresh()  # Hủy timer cũ nếu có
        self._auto_refresh_tick()

    def _stop_auto_refresh(self):
        """Dừng auto-refresh."""
        if self._auto_refresh_id is not None:
            self.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = None

    def _auto_refresh_tick(self):
        """Thực hiện refresh và lên lịch lần tiếp theo."""
        try:
            self._refresh_data()
        except Exception as e:
            print(f"[Auto-refresh] Lỗi: {e}")

        # Lặp lại sau 1 giây nếu vẫn đang chạy
        if self._runner.is_running:
            self._auto_refresh_id = self.after(1000, self._auto_refresh_tick)
        else:
            self._auto_refresh_id = None

    def _safe_log(self, task: str, text: str):
        """Thread-safe: gửi log từ background thread lên GUI + refresh dữ liệu tức thì nếu có file mới."""
        def _update():
            self._log_drawer.append_log(task, text)
            # Tự động reload bảng CSV và danh sách file JSON khi nhận log có thông tin lưu/đổi tên file
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["đã lưu", "đổi tên", "hoàn tất", "phân tích file", "đã đổi tên"]):
                self._refresh_data()

        self.after(0, _update)

    def _on_run_scrape(self):
        """Chạy script cào dữ liệu."""
        if self._runner.is_running:
            return
        self._set_running_state(True)
        self._log_drawer.switch_to_tab("scrape")

        self._runner.run_single(
            "scrape_pancake.py",
            [self._current_page, self._current_date],
            log_callback=lambda t: self._safe_log("scrape", t),
            on_finished=lambda code: self.after(0, lambda: self._on_task_finished(code)),
            workspace_dir=WORKSPACE_DIR,
        )

    def _on_run_extract(self):
        """Chạy script phân tích AI."""
        if self._runner.is_running:
            return
        self._set_running_state(True)
        self._log_drawer.switch_to_tab("extract")

        model = self._data_explorer.get_selected_model()
        self._runner.run_single(
            "extract_ai_cot.py",
            [self._current_page, model, self._current_date],
            log_callback=lambda t: self._safe_log("extract", t),
            on_finished=lambda code: self.after(0, lambda: self._on_task_finished(code)),
            workspace_dir=WORKSPACE_DIR,
        )

    def _on_run_uncheck(self):
        """Chạy script bỏ tag kiểm hàng."""
        if self._runner.is_running:
            return
        self._set_running_state(True)
        self._log_drawer.switch_to_tab("uncheck")

        self._runner.run_single(
            "uncheck_kiem_hang.py",
            [self._current_page],
            log_callback=lambda t: self._safe_log("uncheck", t),
            on_finished=lambda code: self.after(0, lambda: self._on_task_finished(code)),
            workspace_dir=WORKSPACE_DIR,
        )

    def _on_run_all(self):
        """Chạy pipeline tuần tự: Scrape -> Extract -> Uncheck."""
        if self._runner.is_running:
            return
        self._set_running_state(True)
        self._log_drawer.switch_to_tab("scrape")

        model = self._data_explorer.get_selected_model()

        self._runner.run_all(
            page=self._current_page,
            model=model,
            date=self._current_date,
            log_callbacks={
                "scrape": lambda t: self._safe_log("scrape", t),
                "extract": lambda t: self._safe_log("extract", t),
                "uncheck": lambda t: self._safe_log("uncheck", t),
            },
            on_step_change=lambda step: self.after(0, lambda: self._log_drawer.switch_to_tab(step)),
            on_all_finished=lambda success: self.after(0, lambda: self._on_pipeline_finished(success)),
            workspace_dir=WORKSPACE_DIR,
        )

    def _on_stop(self):
        """Dừng task đang chạy."""
        self._runner.stop()
        self._set_running_state(False)

    def _on_task_finished(self, exit_code: int):
        """Callback khi một task đơn lẻ hoàn tất."""
        self._set_running_state(False)
        self._refresh_data()

    def _on_pipeline_finished(self, success: bool):
        """Callback khi pipeline Run All hoàn tất."""
        self._set_running_state(False)
        self._refresh_data()

        if success:
            self._safe_log("uncheck", "🎉 ĐÃ HOÀN TẤT TOÀN BỘ QUY TRÌNH!")
        else:
            self._safe_log("scrape", "⚠️ Pipeline kết thúc có lỗi hoặc bị dừng.")


def main():
    app = PancakeControlApp()
    app.mainloop()


if __name__ == "__main__":
    main()
