"""Budget calculations and chart data."""

from collections import defaultdict
from decimal import Decimal

from financeflow.config import TREND_MONTHS
from financeflow.data.repository import TransactionRepository
from financeflow.domain.entities import (
    Category,
    CategoryTotal,
    MonthlyPoint,
    MonthSummary,
    Transaction,
    TransactionType,
    YearMonth,
)


def _sum_by_kind(transactions: list[Transaction], kind: TransactionType) -> Decimal:
    return sum((t.amount for t in transactions if t.kind is kind), Decimal(0))


class AnalyticsService:
    def __init__(self, transactions: TransactionRepository) -> None:
        self._transactions = transactions

    def month_summary(self, month: YearMonth) -> MonthSummary:
        transactions = self._load_month(month)
        return MonthSummary(
            income=_sum_by_kind(transactions, TransactionType.INCOME),
            expense=_sum_by_kind(transactions, TransactionType.EXPENSE),
        )

    def expense_breakdown(self, month: YearMonth) -> list[CategoryTotal]:
        """Expenses per category for the month, largest first."""
        totals: dict[int, Decimal] = defaultdict(Decimal)
        categories: dict[int, Category] = {}

        for transaction in self._load_month(month):
            if transaction.kind is not TransactionType.EXPENSE:
                continue
            totals[transaction.category.id] += transaction.amount
            categories[transaction.category.id] = transaction.category

        breakdown = [CategoryTotal(categories[cid], total) for cid, total in totals.items()]
        return sorted(breakdown, key=lambda item: item.total, reverse=True)

    def monthly_trend(self, last_month: YearMonth, months_count: int = TREND_MONTHS) -> list[MonthlyPoint]:
        """Income and expense for each of the `months_count` months ending at `last_month`."""
        first_month = last_month.shifted(-(months_count - 1))
        transactions = self._transactions.list_in_range(
            first_month.first_day, last_month.shifted(1).first_day
        )

        income_by_month: dict[YearMonth, Decimal] = defaultdict(Decimal)
        expense_by_month: dict[YearMonth, Decimal] = defaultdict(Decimal)
        for transaction in transactions:
            month = YearMonth.of(transaction.occurred_on)
            if transaction.kind is TransactionType.INCOME:
                income_by_month[month] += transaction.amount
            else:
                expense_by_month[month] += transaction.amount

        points: list[MonthlyPoint] = []
        for offset in range(months_count):
            month = first_month.shifted(offset)
            points.append(
                MonthlyPoint(
                    month=month,
                    income=income_by_month.get(month, Decimal(0)),
                    expense=expense_by_month.get(month, Decimal(0)),
                )
            )
        return points

    def _load_month(self, month: YearMonth) -> list[Transaction]:
        return self._transactions.list_in_range(month.first_day, month.shifted(1).first_day)
