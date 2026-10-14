"""Design tokens and presentation helpers shared by all UI modules."""

from decimal import Decimal
from functools import lru_cache

import customtkinter as ctk

from financeflow.config import CURRENCY_SYMBOL

BACKGROUND = "#F7F7F8"
SURFACE = "#FFFFFF"
HOVER_SURFACE = "#F3F4F6"
BORDER = "#E5E7EB"

TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6B7280"
ON_COLOR = "#FFFFFF"

ACCENT = "#4F46E5"
ACCENT_HOVER = "#4338CA"
ACCENT_SOFT = "#C7D2FE"

INCOME = "#047857"
EXPENSE = "#B91C1C"
DANGER = "#B91C1C"
DANGER_HOVER = "#991B1B"

SUCCESS_SURFACE = "#065F46"
ERROR_SURFACE = "#991B1B"

CARD_CORNER_RADIUS = 12


def apply_global_theme() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


@lru_cache(maxsize=None)
def font(size: int, weight: str = "normal") -> ctk.CTkFont:
    """Return a cached font. Must be called after the root window exists."""
    return ctk.CTkFont(size=size, weight=weight)


def format_money(amount: Decimal) -> str:
    formatted_number = f"{amount:,.2f}".replace(",", "\u00a0").replace("-", "\u2212")
    return f"{formatted_number}\u00a0{CURRENCY_SYMBOL}"
