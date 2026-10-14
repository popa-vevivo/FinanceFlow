"""Main application window: summary cards, transaction list and charts."""

import logging
from collections.abc import Sequence
from decimal import Decimal
from types import TracebackType

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from financeflow.config import APP_NAME
from financeflow.domain.entities import (
    CategoryTotal,
    MonthlyPoint,
    MonthSummary,
    Transaction,
    YearMonth,
)
from financeflow.domain.errors import FinanceFlowError, ValidationError
from financeflow.services.analytics_service import AnalyticsService
from financeflow.services.category_service import CategoryService
from financeflow.services.transaction_service import TransactionService
from financeflow.ui import theme
from financeflow.ui.components.stat_card import StatCard
from financeflow.ui.components.toast import Toast, ToastKind
from financeflow.ui.components.transaction_row import TransactionRow
from financeflow.ui.dialogs.add_transaction import AddTransactionDialog

logger = logging.getLogger(__name__)

_PAGE_PADDING = 24
_GAP = 8
_INITIAL_SIZE = "1080x720"
_MIN_WIDTH = 900
_MIN_HEIGHT = 620


def _format_axis_value(value: float, _position: int) -> str:
    """Compact y-axis labels: 1500000 -> 1.5M, 2500 -> 2.5k."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:g}k"
    return f"{value:g}"


def _describe_savings_rate(summary: MonthSummary) -> str:
    rate = summary.savings_rate
    if rate is None:
        return "Нет доходов за месяц"
    if rate < 0:
        return "Расходы превышают доходы"
    return f"Сбережения: {rate * 100:.0f}% дохода"


class _ChartCard(ctk.CTkFrame):
    """Card with a title and an embedded Matplotlib figure."""

    def __init__(self, master: ctk.CTkBaseClass, title: str) -> None:
        super().__init__(
            master,
            fg_color=theme.SURFACE,
            corner_radius=theme.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER,
        )
        ctk.CTkLabel(
            self,
            text=title,
            font=theme.font(15, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(14, 0))

        self._figure = Figure(figsize=(3.2, 1.8), dpi=100, facecolor=theme.SURFACE)
        self._axes = self._figure.add_subplot(111)
        self._chart_canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def _reset_axes(self) -> None:
        self._axes.clear()
        self._axes.set_axis_on()
        self._axes.set_facecolor(theme.SURFACE)

    def _show_empty_state(self) -> None:
        self._axes.set_axis_off()
        self._axes.text(
            0.5,
            0.5,
            "Нет данных за этот период",
            ha="center",
            va="center",
            color=theme.TEXT_SECONDARY,
            fontsize=11,
            transform=self._axes.transAxes,
        )


class _ExpenseDonutCard(_ChartCard):
    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, "Расходы по категориям")
        self._figure.subplots_adjust(left=0.0, right=0.5, top=0.98, bottom=0.02)

    def show(self, breakdown: Sequence[CategoryTotal]) -> None:
        self._reset_axes()
        if not breakdown:
            self._show_empty_state()
        else:
            grand_total = sum((item.total for item in breakdown), Decimal(0))
            wedges, _ = self._axes.pie(
                [float(item.total) for item in breakdown],
                colors=[item.category.color for item in breakdown],
                startangle=90,
                counterclock=False,
                wedgeprops={"width": 0.4, "edgecolor": theme.SURFACE, "linewidth": 2},
            )
            labels = [
                f"{item.category.name}  {item.total / grand_total * 100:.0f}%"
                for item in breakdown
            ]
            self._axes.legend(
                wedges,
                labels,
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                frameon=False,
                fontsize=9,
                labelcolor=theme.TEXT_PRIMARY,
            )
        self._chart_canvas.draw_idle()


class _TrendCard(_ChartCard):
    _BAR_WIDTH = 0.38

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, "Доходы и расходы за 6 месяцев")
        self._figure.subplots_adjust(left=0.12, right=0.98, top=0.95, bottom=0.14)

    def show(self, points: Sequence[MonthlyPoint]) -> None:
        self._reset_axes()
        has_data = any(point.income or point.expense for point in points)
        if not has_data:
            self._show_empty_state()
        else:
            self._draw_bars(points)
        self._chart_canvas.draw_idle()

    def _draw_bars(self, points: Sequence[MonthlyPoint]) -> None:
        positions = list(range(len(points)))
        half_width = self._BAR_WIDTH / 2

        self._axes.bar(
            [position - half_width for position in positions],
            [float(point.income) for point in points],
            width=self._BAR_WIDTH,
            color=theme.INCOME,
            label="Доходы",
        )
        self._axes.bar(
            [position + half_width for position in positions],
            [float(point.expense) for point in points],
            width=self._BAR_WIDTH,
            color=theme.EXPENSE,
            label="Расходы",
        )

        self._axes.set_xticks(positions)
        self._axes.set_xticklabels([point.month.short_label for point in points])
        self._axes.yaxis.set_major_formatter(FuncFormatter(_format_axis_value))
        self._axes.tick_params(colors=theme.TEXT_SECONDARY, labelsize=9, length=0)
        self._axes.grid(axis="y", color=theme.BORDER, linewidth=0.8)
        self._axes.set_axisbelow(True)
        for side in ("top", "right", "left"):
            self._axes.spines[side].set_visible(False)
        self._axes.spines["bottom"].set_color(theme.BORDER)
        self._axes.legend(
            frameon=False, fontsize=9, loc="upper left", labelcolor=theme.TEXT_PRIMARY
        )


class FinanceFlowApp(ctk.CTk):
    def __init__(
        self,
        transaction_service: TransactionService,
        category_service: CategoryService,
        analytics_service: AnalyticsService,
    ) -> None:
        super().__init__(fg_color=theme.BACKGROUND)
        self._transaction_service = transaction_service
        self._category_service = category_service
        self._analytics_service = analytics_service
        self._displayed_month = YearMonth.today()
        self._add_dialog: AddTransactionDialog | None = None

        self.title(APP_NAME)
        self.geometry(_INITIAL_SIZE)
        self.minsize(_MIN_WIDTH, _MIN_HEIGHT)

        self._build_layout()
        self.bind("<Control-n>", lambda _event: self._open_add_dialog())
        self.refresh()

    def report_callback_exception(
        self,
        exc: type[BaseException],
        val: BaseException,
        tb: TracebackType | None,
    ) -> None:
        """Log unexpected errors and tell the user instead of failing silently."""
        logger.error("Unhandled error in UI callback", exc_info=(exc, val, tb))
        self._toast.show(
            "Произошла непредвиденная ошибка. Подробности записаны в журнал.",
            ToastKind.ERROR,
        )

    def refresh(self) -> None:
        month = self._displayed_month
        try:
            transactions = self._transaction_service.list_for_month(month)
            summary = self._analytics_service.month_summary(month)
            expense_breakdown = self._analytics_service.expense_breakdown(month)
            trend = self._analytics_service.monthly_trend(month)
        except FinanceFlowError as error:
            logger.exception("Failed to load data for %s", month.label)
            self._toast.show(str(error), ToastKind.ERROR)
            return

        self._month_label.configure(text=month.label)
        self._render_summary(summary)
        self._render_transactions(transactions)
        self._expense_chart.show(expense_breakdown)
        self._trend_chart.show(trend)

    # ----- layout -----

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_stat_cards()
        self._build_content()
        self._toast = Toast(self)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=_PAGE_PADDING, pady=(_PAGE_PADDING, 12))
        header.grid_columnconfigure((0, 2), weight=1, uniform="header")

        ctk.CTkLabel(
            header, text=APP_NAME, font=theme.font(22, "bold"), text_color=theme.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        navigator = ctk.CTkFrame(header, fg_color="transparent")
        navigator.grid(row=0, column=1)
        self._make_month_button(navigator, "‹", offset=-1).pack(side="left")
        self._month_label = ctk.CTkLabel(
            navigator,
            text="",
            width=170,
            font=theme.font(16, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        self._month_label.pack(side="left")
        self._make_month_button(navigator, "›", offset=1).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ Добавить",
            height=40,
            font=theme.font(14, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.ON_COLOR,
            command=self._open_add_dialog,
        ).grid(row=0, column=2, sticky="e")

    def _make_month_button(self, parent: ctk.CTkFrame, text: str, offset: int) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            width=40,
            height=40,
            font=theme.font(18, "bold"),
            fg_color=theme.SURFACE,
            hover_color=theme.HOVER_SURFACE,
            text_color=theme.TEXT_PRIMARY,
            border_width=1,
            border_color=theme.BORDER,
            command=lambda: self._change_month(offset),
        )

    def _build_stat_cards(self) -> None:
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=_PAGE_PADDING, pady=(0, 16))
        cards.grid_columnconfigure((0, 1, 2), weight=1, uniform="cards")

        self._income_card = StatCard(cards, "Доходы")
        self._expense_card = StatCard(cards, "Расходы")
        self._balance_card = StatCard(cards, "Баланс")
        self._income_card.grid(row=0, column=0, sticky="ew", padx=(0, _GAP))
        self._expense_card.grid(row=0, column=1, sticky="ew", padx=_GAP)
        self._balance_card.grid(row=0, column=2, sticky="ew", padx=(_GAP, 0))

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=_PAGE_PADDING, pady=(0, _PAGE_PADDING))
        content.grid_columnconfigure(0, weight=3, uniform="content")
        content.grid_columnconfigure(1, weight=2, uniform="content")
        content.grid_rowconfigure(0, weight=1)

        self._build_transaction_list(content)

        charts = ctk.CTkFrame(content, fg_color="transparent")
        charts.grid(row=0, column=1, sticky="nsew", padx=(_GAP, 0))
        charts.grid_columnconfigure(0, weight=1)
        charts.grid_rowconfigure((0, 1), weight=1, uniform="charts")
        self._expense_chart = _ExpenseDonutCard(charts)
        self._trend_chart = _TrendCard(charts)
        self._expense_chart.grid(row=0, column=0, sticky="nsew", pady=(0, _GAP))
        self._trend_chart.grid(row=1, column=0, sticky="nsew", pady=(_GAP, 0))

    def _build_transaction_list(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(
            parent,
            fg_color=theme.SURFACE,
            corner_radius=theme.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER,
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, _GAP))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            panel,
            text="Операции",
            font=theme.font(15, "bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        self._transactions_frame = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self._transactions_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._transactions_frame.grid_columnconfigure(0, weight=1)

    # ----- rendering -----

    def _render_summary(self, summary: MonthSummary) -> None:
        balance_color = theme.INCOME if summary.balance >= 0 else theme.EXPENSE
        self._income_card.set_content(theme.format_money(summary.income), theme.INCOME)
        self._expense_card.set_content(theme.format_money(summary.expense), theme.EXPENSE)
        self._balance_card.set_content(
            theme.format_money(summary.balance),
            balance_color,
            caption=_describe_savings_rate(summary),
        )

    def _render_transactions(self, transactions: Sequence[Transaction]) -> None:
        for child in self._transactions_frame.winfo_children():
            child.destroy()

        if not transactions:
            ctk.CTkLabel(
                self._transactions_frame,
                text="В этом месяце операций пока нет.\nНажмите «+ Добавить» или Ctrl+N.",
                font=theme.font(14),
                text_color=theme.TEXT_SECONDARY,
                justify="center",
            ).grid(row=0, column=0, pady=48)
            return

        for row_index, transaction in enumerate(transactions):
            row = TransactionRow(
                self._transactions_frame, transaction, on_delete=self._delete_transaction
            )
            row.grid(row=row_index, column=0, sticky="ew")

    # ----- actions -----

    def _change_month(self, offset: int) -> None:
        try:
            self._displayed_month = self._displayed_month.shifted(offset)
        except ValidationError as error:
            self._toast.show(str(error), ToastKind.ERROR)
            return
        self.refresh()

    def _open_add_dialog(self) -> None:
        if self._add_dialog is not None and self._add_dialog.winfo_exists():
            self._add_dialog.focus()
            return
        self._add_dialog = AddTransactionDialog(
            self,
            transaction_service=self._transaction_service,
            category_service=self._category_service,
            on_saved=self._handle_transaction_saved,
        )

    def _handle_transaction_saved(self, transaction: Transaction) -> None:
        # Jump to the saved transaction's month so the user immediately sees the result.
        self._displayed_month = YearMonth.of(transaction.occurred_on)
        self.refresh()
        self._toast.show("Операция добавлена")

    def _delete_transaction(self, transaction_id: int) -> None:
        try:
            self._transaction_service.delete_transaction(transaction_id)
        except FinanceFlowError as error:
            self._toast.show(str(error), ToastKind.ERROR)
            return
        self.refresh()
        self._toast.show("Операция удалена")
