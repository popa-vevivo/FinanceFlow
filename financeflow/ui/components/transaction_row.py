"""One row of the transaction list."""

from collections.abc import Callable

import customtkinter as ctk

from financeflow.domain.entities import Transaction, TransactionType
from financeflow.domain.validation import DATE_FORMAT
from financeflow.ui import theme

_MAX_NOTE_LENGTH_SHOWN = 60
_CONFIRM_TIMEOUT_MS = 3000


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


class TransactionRow(ctk.CTkFrame):
    """Shows a transaction; deleting takes two clicks to prevent accidents."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        transaction: Transaction,
        on_delete: Callable[[int], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._transaction_id = transaction.id
        self._on_delete = on_delete
        self._confirm_reset_job: str | None = None
        self._is_confirming_delete = False

        self.grid_columnconfigure(1, weight=1)
        self._build_category_dot(transaction)
        self._build_description(transaction)
        self._build_amount(transaction)
        self._build_delete_button()

        separator = ctk.CTkFrame(self, height=1, fg_color=theme.BORDER)
        separator.grid(row=1, column=0, columnspan=4, sticky="ew")

    def destroy(self) -> None:
        if self._confirm_reset_job is not None:
            self.after_cancel(self._confirm_reset_job)
            self._confirm_reset_job = None
        super().destroy()

    def _build_category_dot(self, transaction: Transaction) -> None:
        dot = ctk.CTkFrame(
            self, width=10, height=10, corner_radius=5, fg_color=transaction.category.color
        )
        dot.grid(row=0, column=0, padx=(4, 12), pady=14)

    def _build_description(self, transaction: Transaction) -> None:
        subtitle = transaction.occurred_on.strftime(DATE_FORMAT)
        if transaction.note:
            subtitle += f" · {_shorten(transaction.note, _MAX_NOTE_LENGTH_SHOWN)}"

        text_block = ctk.CTkFrame(self, fg_color="transparent")
        text_block.grid(row=0, column=1, sticky="w", pady=8)
        ctk.CTkLabel(
            text_block,
            text=transaction.category.name,
            font=theme.font(14, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            text_block,
            text=subtitle,
            font=theme.font(12),
            text_color=theme.TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x")

    def _build_amount(self, transaction: Transaction) -> None:
        is_income = transaction.kind is TransactionType.INCOME
        sign = "+" if is_income else "\u2212"
        ctk.CTkLabel(
            self,
            text=f"{sign}{theme.format_money(transaction.amount)}",
            font=theme.font(14, "bold"),
            text_color=theme.INCOME if is_income else theme.EXPENSE,
        ).grid(row=0, column=2, padx=(12, 8))

    def _build_delete_button(self) -> None:
        self._delete_button = ctk.CTkButton(
            self,
            text="✕",
            width=36,
            height=36,
            font=theme.font(14),
            fg_color="transparent",
            text_color=theme.TEXT_SECONDARY,
            hover_color=theme.HOVER_SURFACE,
            command=self._handle_delete_click,
        )
        self._delete_button.grid(row=0, column=3, padx=(0, 4))

    def _handle_delete_click(self) -> None:
        if self._is_confirming_delete:
            self._on_delete(self._transaction_id)
            return
        self._is_confirming_delete = True
        self._delete_button.configure(
            text="Удалить?",
            width=84,
            fg_color=theme.DANGER,
            hover_color=theme.DANGER_HOVER,
            text_color=theme.ON_COLOR,
        )
        self._confirm_reset_job = self.after(_CONFIRM_TIMEOUT_MS, self._reset_delete_button)

    def _reset_delete_button(self) -> None:
        self._confirm_reset_job = None
        self._is_confirming_delete = False
        self._delete_button.configure(
            text="✕",
            width=36,
            fg_color="transparent",
            hover_color=theme.HOVER_SURFACE,
            text_color=theme.TEXT_SECONDARY,
        )
