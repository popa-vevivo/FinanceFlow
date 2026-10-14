"""Modal dialog for adding an income or an expense."""

from collections.abc import Callable
from datetime import date

import customtkinter as ctk

from financeflow.domain.entities import Transaction, TransactionType
from financeflow.domain.errors import FinanceFlowError
from financeflow.domain.validation import DATE_FORMAT
from financeflow.services.category_service import CategoryService
from financeflow.services.transaction_service import TransactionService
from financeflow.ui import theme

_KIND_LABELS = {
    TransactionType.EXPENSE: "Расход",
    TransactionType.INCOME: "Доход",
}
_KIND_BY_LABEL = {label: kind for kind, label in _KIND_LABELS.items()}

_DIALOG_WIDTH = 400
_DIALOG_HEIGHT = 540
_FORM_PADDING = 24
_ACTIVATION_DELAY_MS = 100


class AddTransactionDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master: ctk.CTk,
        transaction_service: TransactionService,
        category_service: CategoryService,
        on_saved: Callable[[Transaction], None],
    ) -> None:
        super().__init__(master, fg_color=theme.SURFACE)
        self._transaction_service = transaction_service
        self._category_service = category_service
        self._on_saved = on_saved
        self._category_ids_by_name: dict[str, int] = {}
        self._activation_job: str | None = None

        self.title("Новая операция")
        self.resizable(False, False)
        self._center_over(master)
        self.transient(master)

        self._build_form()
        self._load_categories(TransactionType.EXPENSE)

        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self.destroy())
        # Grabbing focus right away fails on some platforms: the window is not visible yet.
        self._activation_job = self.after(_ACTIVATION_DELAY_MS, self._activate)

    def destroy(self) -> None:
        if self._activation_job is not None:
            self.after_cancel(self._activation_job)
            self._activation_job = None
        super().destroy()

    def _center_over(self, master: ctk.CTk) -> None:
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - _DIALOG_WIDTH) // 2
        y = master.winfo_rooty() + (master.winfo_height() - _DIALOG_HEIGHT) // 2
        self.geometry(f"{_DIALOG_WIDTH}x{_DIALOG_HEIGHT}+{max(x, 0)}+{max(y, 0)}")

    def _activate(self) -> None:
        self._activation_job = None
        self.lift()
        self.focus_force()
        self.grab_set()
        self._amount_entry.focus()

    def _build_form(self) -> None:
        self._kind_selector = ctk.CTkSegmentedButton(
            self,
            values=list(_KIND_LABELS.values()),
            command=self._handle_kind_change,
            height=38,
            font=theme.font(14),
            selected_color=theme.ACCENT_SOFT,
            selected_hover_color=theme.ACCENT_SOFT,
            unselected_color=theme.HOVER_SURFACE,
            unselected_hover_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY,
        )
        self._kind_selector.set(_KIND_LABELS[TransactionType.EXPENSE])
        self._kind_selector.pack(fill="x", padx=_FORM_PADDING, pady=(_FORM_PADDING, 16))

        self._amount_entry = self._add_entry("Сумма", placeholder="0.00")

        self._add_field_label("Категория")
        self._category_menu = ctk.CTkOptionMenu(
            self,
            values=[""],
            height=40,
            font=theme.font(14),
            dropdown_font=theme.font(14),
            fg_color=theme.HOVER_SURFACE,
            button_color=theme.BORDER,
            button_hover_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY,
            dropdown_fg_color=theme.SURFACE,
            dropdown_text_color=theme.TEXT_PRIMARY,
            dropdown_hover_color=theme.HOVER_SURFACE,
            anchor="w",
            dynamic_resizing=False,
        )
        self._category_menu.pack(fill="x", padx=_FORM_PADDING, pady=(4, 14))

        self._date_entry = self._add_entry("Дата", placeholder="ДД.ММ.ГГГГ")
        self._date_entry.insert(0, date.today().strftime(DATE_FORMAT))

        self._note_entry = self._add_entry(
            "Заметка (необязательно)", placeholder="Например, обед с коллегами"
        )

        self._error_label = ctk.CTkLabel(
            self,
            text="",
            font=theme.font(13),
            text_color=theme.DANGER,
            wraplength=_DIALOG_WIDTH - 2 * _FORM_PADDING,
            justify="left",
            anchor="w",
        )
        self._error_label.pack(fill="x", padx=_FORM_PADDING, pady=(12, 0))

        ctk.CTkButton(
            self,
            text="Сохранить",
            height=44,
            font=theme.font(15, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.ON_COLOR,
            command=self._save,
        ).pack(fill="x", padx=_FORM_PADDING, pady=(12, _FORM_PADDING))

    def _add_field_label(self, text: str) -> None:
        ctk.CTkLabel(
            self, text=text, font=theme.font(13), text_color=theme.TEXT_SECONDARY, anchor="w"
        ).pack(fill="x", padx=_FORM_PADDING)

    def _add_entry(self, label: str, placeholder: str) -> ctk.CTkEntry:
        self._add_field_label(label)
        entry = ctk.CTkEntry(
            self,
            height=40,
            placeholder_text=placeholder,
            font=theme.font(14),
            fg_color=theme.SURFACE,
            border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY,
        )
        entry.pack(fill="x", padx=_FORM_PADDING, pady=(4, 14))
        return entry

    def _selected_kind(self) -> TransactionType:
        return _KIND_BY_LABEL[self._kind_selector.get()]

    def _handle_kind_change(self, _selected_label: str) -> None:
        self._clear_error()
        self._load_categories(self._selected_kind())

    def _load_categories(self, kind: TransactionType) -> None:
        try:
            categories = self._category_service.list_for_kind(kind)
        except FinanceFlowError as error:
            self._show_error(str(error))
            return

        self._category_ids_by_name = {category.name: category.id for category in categories}
        names = list(self._category_ids_by_name)
        if not names:
            self._category_menu.configure(values=[""])
            self._category_menu.set("")
            self._show_error("Нет доступных категорий.")
            return
        self._category_menu.configure(values=names)
        self._category_menu.set(names[0])

    def _save(self) -> None:
        category_id = self._category_ids_by_name.get(self._category_menu.get())
        if category_id is None:
            self._show_error("Выберите категорию.")
            return

        try:
            transaction = self._transaction_service.add_transaction(
                kind=self._selected_kind(),
                raw_amount=self._amount_entry.get(),
                category_id=category_id,
                raw_date=self._date_entry.get(),
                raw_note=self._note_entry.get(),
            )
        except FinanceFlowError as error:
            self._show_error(str(error))
            return

        self._on_saved(transaction)
        self.destroy()

    def _show_error(self, message: str) -> None:
        self._error_label.configure(text=message)

    def _clear_error(self) -> None:
        self._error_label.configure(text="")
