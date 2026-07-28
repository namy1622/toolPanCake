"""
data_explorer_frame.py - Panel giữa hiển thị bảng CSV kết quả trích xuất AI.
Dùng Custom Table (CTkScrollableFrame) để hỗ trợ tô màu từng ô riêng lẻ.
Bao gồm: Logic validation giá-hộp, ô trống, SĐT trùng/cấm (tương đương extract.js).
"""

import os
import re
import sys
import tkinter as tk
from typing import Callable, Dict, List, Optional

import customtkinter as ctk


# ==========================================
# VALIDATION HELPERS (Chuyển từ extract.js)
# ==========================================

VALID_PRICE_MAP = {
    1: [100000, 110000, 120000, 1100000],
    2: [150000, 160000, 200000],
    4: [240000],
    5: [350000, 380000, 400000, 3800000],
    6: [300000, 320000],
    7: [350000, 400000],
    8: [350000, 400000],
    10: [500000],
}

FLAGGED_PHONES = {"0971838082"}

# Màu sắc validation
COLOR_NORMAL_BG = "#141D2B"
COLOR_NORMAL_FG = "#C8D6E5"
COLOR_WARN_BG = "#2B2510"       # Vàng nhạt - ô trống
COLOR_WARN_FG = "#FBBF24"
COLOR_DANGER_BG = "#2B1515"     # Đỏ nhạt - giá sai hộp
COLOR_DANGER_FG = "#F87171"
COLOR_FLAGGED_BG = "#2B1A13"    # Nâu đỏ - SĐT cấm
COLOR_FLAGGED_FG = "#E8A087"
COLOR_DUP_BG = "#1F1A2E"       # Tím - SĐT trùng
COLOR_DUP_FG = "#C084FC"
COLOR_ROW_HOVER = "#1A2838"
COLOR_ROW_SELECTED = "#1A3D5C"
COLOR_ROW_BORDER = "#1C2535"
COLOR_HEADER_BG = "#1A2332"


def parse_price(price_str: str) -> int:
    if not price_str:
        return 0
    clean = re.sub(r'[^0-9]', '', str(price_str))
    try:
        return int(clean)
    except ValueError:
        return 0


def parse_quantity(qty_str: str) -> Optional[int]:
    if not qty_str:
        return None
    clean = str(qty_str).strip().lower()
    match = re.search(r'(\d+)', clean)
    if match:
        return int(match.group(1))
    return None


def is_empty_value(val: str) -> bool:
    if not val:
        return True
    stripped = val.strip()
    return stripped == '' or stripped == 'Chưa rõ' or stripped == '-'


def validate_price_quantity(price: int, qty: Optional[int]) -> bool:
    if price == 0 or qty is None:
        return True
    if qty in VALID_PRICE_MAP:
        return price in VALID_PRICE_MAP[qty]
    return False


def clean_phone(phone_str: str) -> str:
    if not phone_str:
        return ''
    phone = phone_str.strip()
    if phone.startswith("'"):
        phone = phone[1:]
    return phone


def find_duplicate_phones(data: List[Dict]) -> set:
    phone_count = {}
    for row in data:
        phone = clean_phone(row.get("phone", ""))
        if phone and not is_empty_value(phone):
            phone_count[phone] = phone_count.get(phone, 0) + 1
    return {p for p, count in phone_count.items() if count > 1}


def format_price_display(price_str: str) -> str:
    price_num = parse_price(price_str)
    if price_num > 0:
        return f"{price_num:,}đ".replace(",", ".")
    return price_str or ""


# ==========================================
# CẤU HÌNH CỘT BẢNG
# ==========================================

# (key, heading, pixel_width)
COLUMNS = [
    ("name",     "Khách Hàng",        120),
    ("phone",    "SĐT",              100),
    ("address",  "Địa Chỉ Giao Hàng", 250),
    ("price",    "Giá Chốt",          85),
    ("quantity", "Số Hộp",            55),
    ("product",  "Tên Sản Phẩm",     130),
    ("source",   "File nguồn",       160),
]

ROW_HEIGHT = 30


# ==========================================
# CUSTOM TABLE ROW
# ==========================================

class TableRow(ctk.CTkFrame):
    """Một hàng dữ liệu trong bảng, hỗ trợ tô màu từng ô riêng."""

    def __init__(self, master, row_data: Dict, cell_colors: Dict[str, tuple],
                 on_click: Callable = None, **kwargs):
        super().__init__(master, height=ROW_HEIGHT, corner_radius=0, **kwargs)
        self.configure(fg_color=COLOR_NORMAL_BG, cursor="hand2")
        self.pack_propagate(False)  # Giữ chiều cao cố định

        self._row_data = row_data
        self._on_click = on_click
        self._is_selected = False
        self._cell_labels: Dict[str, ctk.CTkLabel] = {}
        self._cell_frames: Dict[str, ctk.CTkFrame] = {}

        # Tạo container ngang cho các ô
        self._inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._inner.pack(fill="both", expand=True)
        self._inner.bind("<Button-1>", self._handle_click)

        # Tạo từng ô với chiều rộng cố định
        for key, heading, width in COLUMNS:
            bg_color, fg_color = cell_colors.get(key, (COLOR_NORMAL_BG, COLOR_NORMAL_FG))

            cell_frame = ctk.CTkFrame(
                self._inner, fg_color=bg_color, corner_radius=3,
                width=width, height=ROW_HEIGHT - 4,
            )
            cell_frame.pack(side="left", padx=1, pady=2)
            cell_frame.pack_propagate(False)  # Giữ chiều rộng cố định
            cell_frame.bind("<Button-1>", self._handle_click)

            text = str(row_data.get(key, ""))
            label = ctk.CTkLabel(
                cell_frame, text=text,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=fg_color, anchor="w",
                wraplength=0,  # Không wrap - text tràn sẽ bị cắt
            )
            label.pack(fill="both", expand=True, padx=6, pady=1)
            label.bind("<Button-1>", self._handle_click)

            self._cell_labels[key] = label
            self._cell_frames[key] = cell_frame

        self.bind("<Button-1>", self._handle_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def update_row(self, row_data: Dict, cell_colors: Dict[str, tuple], display_data: Dict[str, str]):
        """Cập nhật dữ liệu và màu sắc cho hàng hiện tại mà không tạo lại widget."""
        self._row_data = row_data
        for key, heading, width in COLUMNS:
            bg_color, fg_color = cell_colors.get(key, (COLOR_NORMAL_BG, COLOR_NORMAL_FG))
            if key in self._cell_frames:
                self._cell_frames[key].configure(fg_color=bg_color)
            if key in self._cell_labels:
                text = display_data.get(key, str(row_data.get(key, "")))
                self._cell_labels[key].configure(text=text, text_color=fg_color)

    def _handle_click(self, event=None):
        if self._on_click:
            self._on_click(self)

    def _on_enter(self, event=None):
        if not self._is_selected:
            self.configure(fg_color=COLOR_ROW_HOVER)

    def _on_leave(self, event=None):
        if not self._is_selected:
            self.configure(fg_color=COLOR_NORMAL_BG)

    def set_selected(self, selected: bool):
        self._is_selected = selected
        if selected:
            self.configure(fg_color=COLOR_ROW_SELECTED)
        else:
            self.configure(fg_color=COLOR_NORMAL_BG)

    @property
    def row_data(self) -> Dict:
        return self._row_data


# ==========================================
# DATA EXPLORER FRAME
# ==========================================

class DataExplorerFrame(ctk.CTkFrame):
    """Panel giữa - Bảng dữ liệu CSV kết quả trích xuất AI."""

    def __init__(self, master, models: List[str] = None,
                 on_run_extract=None, on_refresh=None, on_open_folder=None,
                 on_row_select=None, **kwargs):
        super().__init__(master, corner_radius=0, **kwargs)

        self._on_run_extract = on_run_extract
        self._on_refresh = on_refresh
        self._on_open_folder = on_open_folder
        self._on_row_select = on_row_select
        self._csv_data: List[Dict] = []
        self._table_rows: List[TableRow] = []
        self._selected_row: Optional[TableRow] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui(models or [])

    def _build_ui(self, models: List[str]):
        # === HEADER BAR ===
        header = ctk.CTkFrame(self, fg_color="#151D2B", height=44, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")

        title = ctk.CTkLabel(
            header, text="📊 Kết Quả Trích Xuất Phân Tích AI (CSV)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#C8D6E5",
        )
        title.pack(side="left", padx=10, pady=8)

        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(side="right", padx=10, pady=4)

        model_label = ctk.CTkLabel(
            controls, text="Model:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#E74C3C",
        )
        model_label.pack(side="left", padx=(0, 4))

        self._model_var = ctk.StringVar(value=models[0] if models else "")
        self._model_dropdown = ctk.CTkOptionMenu(
            controls, variable=self._model_var,
            values=models if models else ["Không có model"],
            font=ctk.CTkFont(size=11),
            width=160, height=28, corner_radius=6,
            fg_color="#2C3E50", button_color="#1A5276",
            button_hover_color="#2471A3",
            dropdown_fg_color="#1B2838",
            dropdown_hover_color="#2C3E50",
        )
        self._model_dropdown.pack(side="left", padx=4)

        self._btn_extract = ctk.CTkButton(
            controls, text="▶ Chạy AI",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=100, height=28, corner_radius=6,
            fg_color="#2C3E50", hover_color="#34495E",
            border_width=1, border_color="#00B4D8",
            command=self._handle_extract,
        )
        self._btn_extract.pack(side="left", padx=4)

        btn_refresh = ctk.CTkButton(
            controls, text="🔄",
            font=ctk.CTkFont(size=14),
            width=32, height=28, corner_radius=6,
            fg_color="#2C3E50", hover_color="#34495E",
            command=self._handle_refresh,
        )
        btn_refresh.pack(side="left", padx=2)

        btn_folder = ctk.CTkButton(
            controls, text="📁 Thư mục Excel",
            font=ctk.CTkFont(size=11),
            width=110, height=28, corner_radius=6,
            fg_color="#2C3E50", hover_color="#34495E",
            border_width=1, border_color="#00B4D8",
            command=self._handle_open_folder,
        )
        btn_folder.pack(side="left", padx=4)

        # === TABLE AREA ===
        table_container = ctk.CTkFrame(self, fg_color="#111921", corner_radius=0)
        table_container.grid(row=1, column=0, sticky="nsew")
        table_container.grid_rowconfigure(1, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # --- Table Header (cố định, không cuộn) ---
        header_row = ctk.CTkFrame(table_container, fg_color=COLOR_HEADER_BG, height=32, corner_radius=0)
        header_row.grid(row=0, column=0, sticky="ew")
        header_row.pack_propagate(False)

        header_inner = ctk.CTkFrame(header_row, fg_color="transparent")
        header_inner.pack(fill="both", expand=True)

        for key, heading, width in COLUMNS:
            lbl_frame = ctk.CTkFrame(header_inner, fg_color="transparent", width=width, height=28)
            lbl_frame.pack(side="left", padx=1, pady=2)
            lbl_frame.pack_propagate(False)

            lbl = ctk.CTkLabel(
                lbl_frame, text=heading,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#00E5FF", anchor="w",
            )
            lbl.pack(fill="both", expand=True, padx=6, pady=2)

        # --- Table Body (Scrollable) ---
        self._table_body = ctk.CTkScrollableFrame(
            table_container, fg_color="#111921", corner_radius=0,
            scrollbar_button_color="#2C3E50",
            scrollbar_button_hover_color="#34495E",
        )
        self._table_body.grid(row=1, column=0, sticky="nsew")

        # Placeholder
        self._placeholder = ctk.CTkLabel(
            self._table_body,
            text="Đang nạp dữ liệu khách hàng trích xuất...",
            font=ctk.CTkFont(size=11), text_color="#4A5568",
        )
        self._placeholder.pack(pady=40)

    def _handle_extract(self):
        if self._on_run_extract:
            self._on_run_extract()

    def _handle_refresh(self):
        if self._on_refresh:
            self._on_refresh()

    def _handle_open_folder(self):
        if self._on_open_folder:
            self._on_open_folder()

    def _on_row_clicked(self, row_widget: TableRow):
        """Xử lý khi click vào 1 hàng."""
        if self._selected_row:
            self._selected_row.set_selected(False)
        row_widget.set_selected(True)
        self._selected_row = row_widget

        if self._on_row_select:
            self._on_row_select(row_widget.row_data)

    def _get_cell_colors(self, row: Dict, duplicate_phones: set) -> Dict[str, tuple]:
        """
        Trả về dict {column_key: (bg_color, fg_color)} cho từng ô cần tô màu.
        Chỉ tô ô nào có vấn đề, ô bình thường giữ màu mặc định.
        """
        colors = {}

        name = row.get("name", "")
        phone_raw = row.get("phone", "")
        address = row.get("address", "")
        price_str = row.get("price", "")
        qty_str = row.get("quantity", "")

        phone = clean_phone(phone_raw)
        parsed_price = parse_price(price_str)
        parsed_qty = parse_quantity(qty_str)

        is_price_empty = is_empty_value(price_str) or parsed_price == 0
        is_qty_empty = is_empty_value(qty_str) or parsed_qty is None

        # Tô ô Tên nếu trống
        if is_empty_value(name):
            colors["name"] = (COLOR_WARN_BG, COLOR_WARN_FG)

        # Tô ô SĐT: cấm > trùng > trống
        if phone in FLAGGED_PHONES:
            colors["phone"] = (COLOR_FLAGGED_BG, COLOR_FLAGGED_FG)
        elif phone and not is_empty_value(phone) and phone in duplicate_phones:
            colors["phone"] = (COLOR_DUP_BG, COLOR_DUP_FG)
        elif is_empty_value(phone_raw):
            colors["phone"] = (COLOR_WARN_BG, COLOR_WARN_FG)

        # Tô ô Địa chỉ nếu trống
        if is_empty_value(address):
            colors["address"] = (COLOR_WARN_BG, COLOR_WARN_FG)

        # Tô ô Giá & Số hộp: không khớp > trống
        has_mismatch = False
        if not is_price_empty and not is_qty_empty:
            has_mismatch = not validate_price_quantity(parsed_price, parsed_qty)

        if has_mismatch:
            colors["price"] = (COLOR_DANGER_BG, COLOR_DANGER_FG)
            colors["quantity"] = (COLOR_DANGER_BG, COLOR_DANGER_FG)
        else:
            if is_price_empty:
                colors["price"] = (COLOR_WARN_BG, COLOR_WARN_FG)
            if is_qty_empty:
                colors["quantity"] = (COLOR_WARN_BG, COLOR_WARN_FG)

        return colors

    def load_csv_data(self, data: List[Dict]):
        """Nạp dữ liệu CSV vào bảng custom với Incremental Updating siêu mượt."""
        # Nếu dữ liệu y hệt không thay đổi, bỏ qua không làm gì cả
        if self._csv_data == data and len(self._table_rows) == len(data):
            return

        self._csv_data = data

        if not data:
            for row_w in self._table_rows:
                row_w.destroy()
            self._table_rows.clear()
            self._selected_row = None

            if not self._placeholder:
                self._placeholder = ctk.CTkLabel(
                    self._table_body,
                    text="Không có dữ liệu CSV cho ngày đã chọn.\nHãy bấm \"Chạy Phân Tích AI\" để bắt đầu.",
                    font=ctk.CTkFont(size=11), text_color="#4A5568",
                    wraplength=400,
                )
                self._placeholder.pack(pady=40)
            return

        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

        duplicate_phones = find_duplicate_phones(data)

        num_existing = len(self._table_rows)
        num_new = len(data)

        # Cập nhật hàng cũ, thêm hàng mới, xóa hàng dư
        for i in range(max(num_existing, num_new)):
            if i < num_new:
                row = data[i]
                cell_colors = self._get_cell_colors(row, duplicate_phones)

                display_data = {
                    "name": row.get("name", "") or "Chưa rõ",
                    "phone": clean_phone(row.get("phone", "")) or "Chưa rõ",
                    "address": row.get("address", "") or "Chưa rõ",
                    "price": format_price_display(row.get("price", "")),
                    "quantity": row.get("quantity", "") or "-",
                    "product": row.get("product_name", "") or "-",
                    "source": row.get("source_file", ""),
                }

                if "phone" in cell_colors:
                    bg, _ = cell_colors["phone"]
                    if bg == COLOR_FLAGGED_BG:
                        display_data["phone"] = f"🚫 {display_data['phone']}"
                    elif bg == COLOR_DUP_BG:
                        display_data["phone"] = f"🔁 {display_data['phone']}"

                if "price" in cell_colors and cell_colors["price"][0] == COLOR_DANGER_BG:
                    display_data["price"] = f"⚠ {display_data['price']}"
                    display_data["quantity"] = f"⚠ {display_data['quantity']}"

                if i < num_existing:
                    # Incremental update cho hàng đã có (không hủy hay vẽ lại widget)
                    self._table_rows[i].update_row(row, cell_colors, display_data)
                else:
                    # Thêm hàng mới tinh vào cuối
                    row_widget = TableRow(
                        self._table_body,
                        row_data=row.copy(),
                        cell_colors=cell_colors,
                        on_click=self._on_row_clicked,
                    )
                    for key, label in row_widget._cell_labels.items():
                        if key in display_data:
                            label.configure(text=display_data[key])

                    row_widget.pack(fill="x", padx=0, pady=0)
                    self._table_rows.append(row_widget)
            else:
                # Xóa hàng dư thừa nếu dataset nhỏ đi
                excess_row = self._table_rows[num_new]
                if excess_row == self._selected_row:
                    self._selected_row = None
                excess_row.destroy()
                self._table_rows.pop(num_new)

    def get_selected_model(self) -> str:
        return self._model_var.get()

    def update_models(self, models: List[str]):
        if models:
            self._model_dropdown.configure(values=models)
            self._model_var.set(models[0])
        else:
            self._model_dropdown.configure(values=["Không có model"])

    def set_extract_enabled(self, enabled: bool):
        if enabled:
            self._btn_extract.configure(state="normal", fg_color="#2C3E50")
        else:
            self._btn_extract.configure(state="disabled", fg_color="#4A5A6A")
