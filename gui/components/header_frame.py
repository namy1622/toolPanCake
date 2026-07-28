"""
header_frame.py - Thanh tiêu đề trên cùng của ứng dụng.
Chứa: Logo, Chọn trang Pancake, Chọn ngày làm việc, Nút Chạy Tất Cả / Dừng.
"""

import datetime
import customtkinter as ctk
from tkcalendar import DateEntry


class HeaderFrame(ctk.CTkFrame):
    """Thanh điều khiển header phía trên cùng."""

    def __init__(self, master, on_page_change=None, on_date_change=None,
                 on_run_all=None, on_stop=None, **kwargs):
        super().__init__(master, height=70, corner_radius=0, **kwargs)

        self._on_page_change = on_page_change
        self._on_date_change = on_date_change
        self._on_run_all = on_run_all
        self._on_stop = on_stop

        self._selected_page = "1"
        self._page_buttons = {}

        self.grid_columnconfigure(1, weight=1)
        self._build_ui()

    def _build_ui(self):
        # === LOGO AREA (Cột 0) ===
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=(15, 10), pady=8, sticky="w")

        title_label = ctk.CTkLabel(
            logo_frame, text="⬡ PANCAKE CONTROL",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#00E5FF"
        )
        title_label.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            logo_frame, text="Hệ thống Điều phối & Phân tích Đơn hàng",
            font=ctk.CTkFont(size=10), text_color="#8892A4"
        )
        subtitle.pack(anchor="w")

        # === PAGE SELECTOR (Cột 1) ===
        page_area = ctk.CTkFrame(self, fg_color="transparent")
        page_area.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        page_label = ctk.CTkLabel(
            page_area, text="CHỌN TRANG CÀO:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#8892A4"
        )
        page_label.pack(side="left", padx=(0, 10))

        pages_data = {
            "1": "Dây Thìa Canh",
            "2": "Trà Đông Trùng",
        }

        for page_id, name in pages_data.items():
            btn = ctk.CTkButton(
                page_area, text=name,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=140, height=36, corner_radius=8,
                fg_color="#1A5276" if page_id == "1" else "#2C3E50",
                hover_color="#2471A3",
                border_width=2,
                border_color="#00E5FF" if page_id == "1" else "#3B4A5C",
                command=lambda pid=page_id: self._select_page(pid),
            )
            btn.pack(side="left", padx=4)
            self._page_buttons[page_id] = btn

        # === DATE PICKER & ACTIONS (Cột 2) ===
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=0, column=2, padx=(10, 15), pady=8, sticky="e")

        date_label = ctk.CTkLabel(
            controls_frame, text="NGÀY:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#E74C3C"
        )
        date_label.pack(side="left", padx=(0, 5))

        # DateEntry widget từ tkcalendar
        self._date_entry = DateEntry(
            controls_frame,
            date_pattern="dd.mm.yy",
            width=10,
            font=("Segoe UI", 11),
            background="#1B2838",
            foreground="#E0E0E0",
            headersbackground="#1A5276",
            headersforeground="white",
            selectbackground="#00E5FF",
            selectforeground="black",
            normalbackground="#1B2838",
            normalforeground="#E0E0E0",
            weekendbackground="#1B2838",
            weekendforeground="#E0E0E0",
        )
        self._date_entry.pack(side="left", padx=(0, 12))
        self._date_entry.bind("<<DateEntrySelected>>", self._on_date_selected)

        # Nút Chạy Tất Cả
        self._btn_run_all = ctk.CTkButton(
            controls_frame, text="▶ Chạy Tất Cả",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=130, height=34, corner_radius=8,
            fg_color="#27AE60", hover_color="#2ECC71",
            command=self._handle_run_all,
        )
        self._btn_run_all.pack(side="left", padx=4)

        # Nút Dừng
        self._btn_stop = ctk.CTkButton(
            controls_frame, text="⏹ Dừng",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=90, height=34, corner_radius=8,
            fg_color="#7F8C8D", hover_color="#E74C3C",
            state="disabled",
            command=self._handle_stop,
        )
        self._btn_stop.pack(side="left", padx=4)

    def _select_page(self, page_id: str):
        """Chuyển trang Pancake được chọn."""
        self._selected_page = page_id

        # Cập nhật giao diện button
        for pid, btn in self._page_buttons.items():
            if pid == page_id:
                btn.configure(
                    fg_color="#1A5276",
                    border_color="#00E5FF",
                )
            else:
                btn.configure(
                    fg_color="#2C3E50",
                    border_color="#3B4A5C",
                )

        if self._on_page_change:
            self._on_page_change(page_id)

    def _on_date_selected(self, event=None):
        if self._on_date_change:
            self._on_date_change(self.get_date_str())

    def _handle_run_all(self):
        if self._on_run_all:
            self._on_run_all()

    def _handle_stop(self):
        if self._on_stop:
            self._on_stop()

    def get_selected_page(self) -> str:
        return self._selected_page

    def get_date_str(self) -> str:
        """Lấy ngày đã chọn dưới dạng chuỗi dd.mm.yy"""
        date_obj = self._date_entry.get_date()
        return date_obj.strftime("%d.%m.%y")

    def set_running_state(self, is_running: bool):
        """Chuyển đổi trạng thái nút khi có/không task đang chạy."""
        if is_running:
            self._btn_run_all.configure(state="disabled", fg_color="#4A5A6A")
            self._btn_stop.configure(state="normal", fg_color="#E74C3C")
        else:
            self._btn_run_all.configure(state="normal", fg_color="#27AE60")
            self._btn_stop.configure(state="disabled", fg_color="#7F8C8D")
