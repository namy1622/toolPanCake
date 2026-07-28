"""
file_browser_frame.py - Panel bên trái hiển thị danh sách file JSON đã cào.
Hỗ trợ Cập nhật thông minh (Incremental Update) - không hủy và dựng lại widget vô ích, giúp UI siêu mượt.
"""

import customtkinter as ctk
from typing import Callable, Dict, List, Optional


class FileItem(ctk.CTkFrame):
    """Widget đại diện cho 1 file JSON trong danh sách."""

    def __init__(self, master, file_info: Dict, on_click: Callable = None, **kwargs):
        super().__init__(master, height=38, corner_radius=6, **kwargs)

        self._file_info = file_info
        self._on_click = on_click
        self._is_selected = False

        self.configure(
            fg_color="#1E2A3A" if not file_info.get("is_processed") else "#1A3325",
            cursor="hand2"
        )

        self.bind("<Button-1>", self._handle_click)

        icon = "✅ " if file_info.get("is_processed") else "📄 "
        self._name_label = ctk.CTkLabel(
            self, text=f"{icon}{file_info['name']}",
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            text_color="#C8D6E5",
            anchor="w",
        )
        self._name_label.pack(side="left", fill="x", expand=True, padx=8, pady=4)
        self._name_label.bind("<Button-1>", self._handle_click)

        size_kb = file_info.get("size", 0) / 1024
        self._size_label = ctk.CTkLabel(
            self, text=f"{size_kb:.1f}KB",
            font=ctk.CTkFont(size=10), text_color="#6C7A89",
        )
        self._size_label.pack(side="right", padx=8)
        self._size_label.bind("<Button-1>", self._handle_click)

    def update_info(self, file_info: Dict):
        """Cập nhật thông tin file mà không cần hủy widget."""
        self._file_info = file_info
        is_done = file_info.get("is_processed", False)
        icon = "✅ " if is_done else "📄 "
        self._name_label.configure(text=f"{icon}{file_info['name']}")

        size_kb = file_info.get("size", 0) / 1024
        self._size_label.configure(text=f"{size_kb:.1f}KB")

        if not self._is_selected:
            self.configure(fg_color="#1A3325" if is_done else "#1E2A3A")

    def _handle_click(self, event=None):
        if self._on_click:
            self._on_click(self._file_info)

    def set_selected(self, selected: bool):
        self._is_selected = selected
        if selected:
            self.configure(fg_color="#1A3D5C", border_width=1, border_color="#00E5FF")
        else:
            is_done = self._file_info.get("is_processed", False)
            self.configure(
                fg_color="#1A3325" if is_done else "#1E2A3A",
                border_width=0,
            )


class FileBrowserFrame(ctk.CTkFrame):
    """Panel bên trái - Duyệt danh sách file JSON."""

    def __init__(self, master, on_file_select=None, on_run_scrape=None, **kwargs):
        super().__init__(master, width=280, corner_radius=0, **kwargs)

        self._on_file_select = on_file_select
        self._on_run_scrape = on_run_scrape
        self._file_items_map: Dict[str, FileItem] = {}  # {filename: FileItem}
        self._file_items_list: List[FileItem] = []
        self._selected_item: Optional[FileItem] = None

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        # === HEADER ===
        header = ctk.CTkFrame(self, fg_color="#151D2B", height=40, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header, text="📁 Hồ Sơ Cuộc Trò Chuyện (JSON)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#C8D6E5",
            anchor="w",
        )
        title.grid(row=0, column=0, padx=10, pady=6, sticky="w")

        self._file_count_label = ctk.CTkLabel(
            header, text="0 files",
            font=ctk.CTkFont(size=10), text_color="#6C7A89",
        )
        self._file_count_label.grid(row=0, column=1, padx=10, pady=6, sticky="e")

        # === TOOLBAR ===
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=36)
        toolbar.grid(row=1, column=0, sticky="ew", padx=6, pady=(4, 2))

        self._btn_scrape = ctk.CTkButton(
            toolbar, text="⬇ Chạy Cào Dữ Liệu",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30, corner_radius=6,
            fg_color="#2C3E50", hover_color="#34495E",
            border_width=1, border_color="#00B4D8",
            command=self._handle_run_scrape,
        )
        self._btn_scrape.pack(fill="x", padx=2)

        # === FILE LIST (Scrollable) ===
        self._file_list = ctk.CTkScrollableFrame(
            self, fg_color="#111921", corner_radius=0,
            scrollbar_button_color="#2C3E50",
            scrollbar_button_hover_color="#34495E",
        )
        self._file_list.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        # Placeholder khi chưa có file
        self._placeholder = ctk.CTkLabel(
            self._file_list,
            text="Chọn trang & ngày để tải danh sách file...",
            font=ctk.CTkFont(size=11), text_color="#4A5568",
            wraplength=230,
        )
        self._placeholder.pack(pady=40)

    def _handle_run_scrape(self):
        if self._on_run_scrape:
            self._on_run_scrape()

    def load_files(self, files: List[Dict]):
        """Nạp danh sách file JSON vào panel với Incremental Updating siêu mượt."""
        if not files:
            # Xóa toàn bộ nếu không có file
            for item in self._file_items_list:
                item.destroy()
            self._file_items_list.clear()
            self._file_items_map.clear()
            self._selected_item = None

            if not self._placeholder:
                self._placeholder = ctk.CTkLabel(
                    self._file_list,
                    text="Không tìm thấy file JSON nào cho ngày đã chọn.",
                    font=ctk.CTkFont(size=11), text_color="#4A5568",
                    wraplength=230,
                )
                self._placeholder.pack(pady=40)
            self._file_count_label.configure(text="0 files")
            return

        # Ẩn placeholder nếu đang có
        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

        self._file_count_label.configure(text=f"{len(files)} files")

        new_names = {f["name"] for f in files}

        # Xóa các file không còn tồn tại
        for name in list(self._file_items_map.keys()):
            if name not in new_names:
                item = self._file_items_map.pop(name)
                if item in self._file_items_list:
                    self._file_items_list.remove(item)
                if item == self._selected_item:
                    self._selected_item = None
                item.destroy()

        # Cập nhật hoặc thêm mới từng file
        for file_info in files:
            name = file_info["name"]
            if name in self._file_items_map:
                # Cập nhật item đã có (nếu trạng thái/dung lượng thay đổi)
                self._file_items_map[name].update_info(file_info)
            else:
                # Tạo item mới và pack vào danh sách
                item = FileItem(
                    self._file_list,
                    file_info=file_info,
                    on_click=self._on_item_click,
                    fg_color="#1E2A3A",
                )
                item.pack(fill="x", padx=4, pady=2)
                self._file_items_map[name] = item
                self._file_items_list.append(item)

    def _on_item_click(self, file_info: Dict):
        if self._selected_item:
            self._selected_item.set_selected(False)

        name = file_info["name"]
        if name in self._file_items_map:
            item = self._file_items_map[name]
            item.set_selected(True)
            self._selected_item = item

        if self._on_file_select:
            self._on_file_select(file_info)

    def set_scrape_enabled(self, enabled: bool):
        if enabled:
            self._btn_scrape.configure(state="normal", fg_color="#2C3E50")
        else:
            self._btn_scrape.configure(state="disabled", fg_color="#4A5A6A")
