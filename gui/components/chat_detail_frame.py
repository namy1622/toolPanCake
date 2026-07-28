"""
chat_detail_frame.py - Panel bên phải hiển thị chi tiết chat & lập luận AI.
Chứa: Tên khách hàng, File nguồn, Box lập luận AI, Bong bóng tin nhắn hội thoại.
"""

import customtkinter as ctk
from typing import Dict, List, Optional


class ChatBubble(ctk.CTkFrame):
    """Widget bong bóng tin nhắn đơn lẻ."""

    def __init__(self, master, sender: str, content: str, is_shop: bool = False, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        if is_shop:
            self.configure(fg_color="#1A3D5C")
            anchor = "e"
            text_color = "#B2EBF2"
            sender_color = "#00E5FF"
        else:
            self.configure(fg_color="#2C3E50")
            anchor = "w"
            text_color = "#E0E0E0"
            sender_color = "#F39C12"

        # Sender name
        sender_label = ctk.CTkLabel(
            self, text=sender,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=sender_color, anchor="w",
        )
        sender_label.pack(fill="x", padx=10, pady=(6, 0))

        # Content text
        content_label = ctk.CTkLabel(
            self, text=content,
            font=ctk.CTkFont(size=11),
            text_color=text_color,
            wraplength=280,
            justify="left", anchor="w",
        )
        content_label.pack(fill="x", padx=10, pady=(2, 8))


class ChatDetailFrame(ctk.CTkFrame):
    """Panel bên phải - Hiển thị lịch sử chat và lập luận AI."""

    def __init__(self, master, **kwargs):
        super().__init__(master, width=340, corner_radius=0, **kwargs)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        # === HEADER ===
        self._header = ctk.CTkFrame(self, fg_color="#151D2B", height=50, corner_radius=0)
        self._header.grid(row=0, column=0, sticky="ew")

        self._name_label = ctk.CTkLabel(
            self._header, text="💬 Chi Tiết Hội Thoại",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#C8D6E5",
        )
        self._name_label.pack(side="left", padx=10, pady=4)

        self._source_label = ctk.CTkLabel(
            self._header, text="",
            font=ctk.CTkFont(size=10), text_color="#6C7A89",
        )
        self._source_label.pack(side="right", padx=10, pady=4)

        # === AI REASONING BOX ===
        ai_section = ctk.CTkFrame(self, fg_color="#111921", corner_radius=0)
        ai_section.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        ai_badge = ctk.CTkLabel(
            ai_section, text="🤖 Lập luận tính số hộp của AI:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#F1C40F",
            anchor="w",
        )
        ai_badge.pack(fill="x", padx=10, pady=(8, 4))

        self._ai_textbox = ctk.CTkTextbox(
            ai_section,
            height=80, corner_radius=6,
            fg_color="#1A2332",
            text_color="#E0E0E0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            wrap="word",
            border_width=1, border_color="#2C3E50",
        )
        self._ai_textbox.pack(fill="x", padx=8, pady=(0, 8))
        self._ai_textbox.insert("1.0", "Chọn một hàng trong bảng CSV hoặc file JSON để xem chi tiết.")
        self._ai_textbox.configure(state="disabled")

        # === CHAT DIALOG (Scrollable) ===
        chat_badge_frame = ctk.CTkFrame(self, fg_color="#111921", height=30, corner_radius=0)
        chat_badge_frame.grid(row=2, column=0, sticky="new", padx=0, pady=0)

        chat_badge = ctk.CTkLabel(
            chat_badge_frame, text="💬 Nội dung cuộc trò chuyện:",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#00E5FF",
            anchor="w",
        )
        chat_badge.pack(fill="x", padx=10, pady=(8, 4))

        self._chat_scroll = ctk.CTkScrollableFrame(
            self, fg_color="#111921", corner_radius=0,
            scrollbar_button_color="#2C3E50",
            scrollbar_button_hover_color="#34495E",
        )
        self._chat_scroll.grid(row=2, column=0, sticky="nsew", padx=0, pady=(30, 0))

        # Placeholder
        self._placeholder = ctk.CTkLabel(
            self._chat_scroll,
            text="Nhấp chọn một hàng trong bảng CSV bên trái\nhoặc một File JSON để đối chiếu\nlịch sử chat và lập luận AI.",
            font=ctk.CTkFont(size=11), text_color="#4A5568",
            wraplength=280, justify="center",
        )
        self._placeholder.pack(pady=60)

        self._chat_bubbles: List[ChatBubble] = []

    def show_chat_detail(self, customer_name: str, source_file: str,
                         ai_reasoning: str, messages: List[Dict]):
        """
        Hiển thị chi tiết cho khách hàng được chọn.

        Args:
            customer_name: Tên khách hàng
            source_file: Tên file nguồn
            ai_reasoning: Văn bản lập luận AI
            messages: Danh sách tin nhắn [{"sender": ..., "content": ...}, ...]
        """
        # Cập nhật header
        self._name_label.configure(text=f"👤 {customer_name}")
        self._source_label.configure(text=source_file)

        # Cập nhật AI reasoning
        self._ai_textbox.configure(state="normal")
        self._ai_textbox.delete("1.0", "end")
        self._ai_textbox.insert("1.0", ai_reasoning or "Không có dữ liệu lập luận AI.")
        self._ai_textbox.configure(state="disabled")

        # Xóa bong bóng chat cũ
        if self._placeholder:
            self._placeholder.destroy()
            self._placeholder = None

        for bubble in self._chat_bubbles:
            bubble.destroy()
        self._chat_bubbles.clear()

        # Tạo bong bóng chat mới
        if not messages:
            no_msg = ctk.CTkLabel(
                self._chat_scroll,
                text="Không có tin nhắn nào.",
                font=ctk.CTkFont(size=11), text_color="#4A5568",
            )
            no_msg.pack(pady=40)
            self._chat_bubbles.append(no_msg)
            return

        for msg in messages:
            sender = msg.get("sender", "Unknown")
            content = msg.get("content", "")
            is_shop = (sender == "Tôi")

            bubble = ChatBubble(
                self._chat_scroll,
                sender=sender,
                content=content,
                is_shop=is_shop,
            )

            if is_shop:
                bubble.pack(fill="x", padx=(40, 6), pady=3, anchor="e")
            else:
                bubble.pack(fill="x", padx=(6, 40), pady=3, anchor="w")

            self._chat_bubbles.append(bubble)

    def clear_detail(self):
        """Xóa toàn bộ nội dung chi tiết, trở về placeholder."""
        self._name_label.configure(text="💬 Chi Tiết Hội Thoại")
        self._source_label.configure(text="")

        self._ai_textbox.configure(state="normal")
        self._ai_textbox.delete("1.0", "end")
        self._ai_textbox.insert("1.0", "Chọn một hàng trong bảng CSV hoặc file JSON để xem chi tiết.")
        self._ai_textbox.configure(state="disabled")

        for bubble in self._chat_bubbles:
            bubble.destroy()
        self._chat_bubbles.clear()

        if not self._placeholder:
            self._placeholder = ctk.CTkLabel(
                self._chat_scroll,
                text="Nhấp chọn một hàng trong bảng CSV bên trái\nhoặc một File JSON để đối chiếu\nlịch sử chat và lập luận AI.",
                font=ctk.CTkFont(size=11), text_color="#4A5568",
                wraplength=280, justify="center",
            )
            self._placeholder.pack(pady=60)
