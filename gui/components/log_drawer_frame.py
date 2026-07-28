"""
log_drawer_frame.py - Panel đáy hiển thị log terminal thời gian thực.
Chứa: Thanh tiêu đề thu gọn/mở rộng, Tab log (Cào/AI/Bỏ Tag), Ô log terminal nền đen.
"""

import customtkinter as ctk
from typing import Dict, Optional


class LogTerminalPane(ctk.CTkFrame):
    """Một ô terminal log nền đen cho một task cụ thể."""

    def __init__(self, master, title: str = "", **kwargs):
        super().__init__(master, corner_radius=0, **kwargs)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Sub-header
        sub_header = ctk.CTkFrame(self, fg_color="#0D1117", height=28, corner_radius=0)
        sub_header.grid(row=0, column=0, sticky="ew")

        sub_title = ctk.CTkLabel(
            sub_header, text=title,
            font=ctk.CTkFont(size=10), text_color="#6C7A89",
        )
        sub_title.pack(side="left", padx=10, pady=2)

        # Checkbox tự cuộn
        self._auto_scroll = ctk.BooleanVar(value=True)
        auto_scroll_cb = ctk.CTkCheckBox(
            sub_header, text="Tự cuộn",
            font=ctk.CTkFont(size=10),
            variable=self._auto_scroll,
            width=20, height=20,
            checkbox_width=16, checkbox_height=16,
            fg_color="#00B4D8", hover_color="#00E5FF",
        )
        auto_scroll_cb.pack(side="right", padx=6, pady=2)

        # Nút Xóa log
        btn_clear = ctk.CTkButton(
            sub_header, text="Xóa",
            font=ctk.CTkFont(size=10),
            width=40, height=22, corner_radius=4,
            fg_color="#2C3E50", hover_color="#E74C3C",
            command=self.clear_log,
        )
        btn_clear.pack(side="right", padx=4, pady=2)

        # Terminal textbox
        self._textbox = ctk.CTkTextbox(
            self,
            fg_color="#0D1117",
            text_color="#39FF14",
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            wrap="word",
            corner_radius=0,
            border_width=0,
        )
        self._textbox.grid(row=1, column=0, sticky="nsew")
        self._textbox.configure(state="disabled")

    def append_log(self, text: str):
        """Thêm một dòng log vào terminal."""
        self._textbox.configure(state="normal")
        self._textbox.insert("end", text + "\n")
        self._textbox.configure(state="disabled")

        if self._auto_scroll.get():
            self._textbox.see("end")

    def clear_log(self):
        """Xóa toàn bộ log."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")


class LogDrawerFrame(ctk.CTkFrame):
    """Panel Log Drawer ở cuối cửa sổ - có thể thu gọn/mở rộng."""

    def __init__(self, master, on_run_uncheck=None, **kwargs):
        super().__init__(master, corner_radius=0, **kwargs)

        self._on_run_uncheck = on_run_uncheck
        self._is_expanded = True
        self._expanded_height = 250

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        # === DRAWER HEADER (Thanh tiêu đề, luôn hiển thị) ===
        self._drawer_header = ctk.CTkFrame(self, fg_color="#0F1520", height=36, corner_radius=0)
        self._drawer_header.grid(row=0, column=0, sticky="ew")

        # Tiêu đề
        title = ctk.CTkLabel(
            self._drawer_header,
            text="📟 BẢNG ĐIỀU KHIỂN & NHẬT KÝ BẢN CHẠY (LOG TERMINALS)",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#8892A4",
        )
        title.pack(side="left", padx=10, pady=6)

        # Stats inline
        stats_frame = ctk.CTkFrame(self._drawer_header, fg_color="transparent")
        stats_frame.pack(side="left", padx=15)

        self._stat_total = ctk.CTkLabel(
            stats_frame, text="Đã quét: 0",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#00E5FF",
        )
        self._stat_total.pack(side="left", padx=6)

        self._stat_success = ctk.CTkLabel(
            stats_frame, text="Bỏ tag: 0",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#2ECC71",
        )
        self._stat_success.pack(side="left", padx=6)

        self._stat_skip = ctk.CTkLabel(
            stats_frame, text="Bỏ qua: 0",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#F1C40F",
        )
        self._stat_skip.pack(side="left", padx=6)

        # Nút bên phải
        right_actions = ctk.CTkFrame(self._drawer_header, fg_color="transparent")
        right_actions.pack(side="right", padx=10)

        # Nút chạy Bỏ Tag
        self._btn_uncheck = ctk.CTkButton(
            right_actions, text="✓ Chạy Bỏ Tag Kiểm Hàng",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=180, height=26, corner_radius=6,
            fg_color="#2C3E50", hover_color="#34495E",
            border_width=1, border_color="#00B4D8",
            command=self._handle_uncheck,
        )
        self._btn_uncheck.pack(side="left", padx=8)

        # Connection badge
        self._connection_badge = ctk.CTkLabel(
            right_actions, text="● Desktop App",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#2ECC71",
        )
        self._connection_badge.pack(side="left", padx=6)

        # Nút toggle
        self._btn_toggle = ctk.CTkButton(
            right_actions, text="▼",
            font=ctk.CTkFont(size=14),
            width=28, height=26, corner_radius=6,
            fg_color="#2C3E50", hover_color="#34495E",
            command=self._toggle_drawer,
        )
        self._btn_toggle.pack(side="left", padx=4)

        # === DRAWER BODY (Nội dung log, có thể ẩn) ===
        self._drawer_body = ctk.CTkFrame(self, fg_color="#0D1117", corner_radius=0)
        self._drawer_body.grid(row=1, column=0, sticky="nsew")
        self._drawer_body.grid_rowconfigure(1, weight=1)
        self._drawer_body.grid_columnconfigure(0, weight=1)

        # Tab buttons
        tab_bar = ctk.CTkFrame(self._drawer_body, fg_color="#0D1117", height=30, corner_radius=0)
        tab_bar.grid(row=0, column=0, sticky="ew")

        self._tabs = {}
        self._tab_buttons = {}
        tab_names = {
            "scrape": "Logs Cào Dữ Liệu",
            "extract": "Logs Phân Tích AI",
            "uncheck": "Logs Bỏ Tag",
        }

        for tab_id, tab_name in tab_names.items():
            btn = ctk.CTkButton(
                tab_bar, text=tab_name,
                font=ctk.CTkFont(size=11),
                height=26, corner_radius=4,
                fg_color="#1A2332" if tab_id == "scrape" else "transparent",
                hover_color="#1A2332",
                text_color="#00E5FF" if tab_id == "scrape" else "#6C7A89",
                command=lambda tid=tab_id: self._switch_tab(tid),
            )
            btn.pack(side="left", padx=2, pady=2)
            self._tab_buttons[tab_id] = btn

        # Terminal panes container
        self._pane_container = ctk.CTkFrame(self._drawer_body, fg_color="#0D1117", corner_radius=0)
        self._pane_container.grid(row=1, column=0, sticky="nsew")
        self._pane_container.grid_rowconfigure(0, weight=1)
        self._pane_container.grid_columnconfigure(0, weight=1)

        terminal_titles = {
            "scrape": "Logs - Trình cào dữ liệu Pancake (Playwright CDP Scraper)",
            "extract": "Logs - Trình trích xuất phân tích trí tuệ nhân tạo (OpenAI API)",
            "uncheck": "Logs - Trình tự động gỡ nhãn Kiểm Hàng (Pancake Automator)",
        }

        for tab_id, title in terminal_titles.items():
            pane = LogTerminalPane(self._pane_container, title=title, fg_color="#0D1117")
            pane.grid(row=0, column=0, sticky="nsew")
            pane.append_log(f"Sẵn sàng...")
            self._tabs[tab_id] = pane

        # Mặc định hiển thị tab scrape
        self._current_tab = "scrape"
        self._tabs["scrape"].tkraise()

    def _switch_tab(self, tab_id: str):
        """Chuyển tab log."""
        self._current_tab = tab_id

        for tid, btn in self._tab_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color="#1A2332", text_color="#00E5FF")
            else:
                btn.configure(fg_color="transparent", text_color="#6C7A89")

        self._tabs[tab_id].tkraise()

    def _toggle_drawer(self):
        """Thu gọn / mở rộng drawer."""
        if self._is_expanded:
            self._drawer_body.grid_forget()
            self._btn_toggle.configure(text="▲")
            self._is_expanded = False
        else:
            self._drawer_body.grid(row=1, column=0, sticky="nsew")
            self._btn_toggle.configure(text="▼")
            self._is_expanded = True

    def _handle_uncheck(self):
        if self._on_run_uncheck:
            self._on_run_uncheck()

    def append_log(self, task: str, text: str):
        """Thêm dòng log vào tab tương ứng."""
        if task in self._tabs:
            self._tabs[task].append_log(text)

    def clear_log(self, task: str):
        """Xóa log của tab cụ thể."""
        if task in self._tabs:
            self._tabs[task].clear_log()

    def switch_to_tab(self, tab_id: str):
        """Tự động chuyển sang tab đang chạy."""
        if tab_id in self._tabs:
            self._switch_tab(tab_id)

    def update_stats(self, total: int = 0, success: int = 0, skip: int = 0):
        """Cập nhật số liệu thống kê inline."""
        self._stat_total.configure(text=f"Đã quét: {total}")
        self._stat_success.configure(text=f"Bỏ tag: {success}")
        self._stat_skip.configure(text=f"Bỏ qua: {skip}")

    def set_uncheck_enabled(self, enabled: bool):
        if enabled:
            self._btn_uncheck.configure(state="normal", fg_color="#2C3E50")
        else:
            self._btn_uncheck.configure(state="disabled", fg_color="#4A5A6A")
