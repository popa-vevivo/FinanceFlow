"""Card showing one headline number (income, expenses, balance)."""

import customtkinter as ctk

from financeflow.ui import theme


class StatCard(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, title: str) -> None:
        super().__init__(
            master,
            fg_color=theme.SURFACE,
            corner_radius=theme.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER,
        )
        self._title_label = ctk.CTkLabel(
            self, text=title, font=theme.font(13), text_color=theme.TEXT_SECONDARY, anchor="w"
        )
        self._value_label = ctk.CTkLabel(
            self, text="—", font=theme.font(24, "bold"), text_color=theme.TEXT_PRIMARY, anchor="w"
        )
        self._caption_label = ctk.CTkLabel(
            self, text="", font=theme.font(12), text_color=theme.TEXT_SECONDARY, anchor="w"
        )
        self._title_label.pack(fill="x", padx=16, pady=(14, 0))
        self._value_label.pack(fill="x", padx=16)
        self._caption_label.pack(fill="x", padx=16, pady=(0, 14))

    def set_content(self, value: str, value_color: str = theme.TEXT_PRIMARY, caption: str = "") -> None:
        self._value_label.configure(text=value, text_color=value_color)
        self._caption_label.configure(text=caption)
