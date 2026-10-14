"""Domain entities: plain data objects with no I/O or UI dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from financeflow.domain.errors import ValidationError

MONEY_QUANTUM = Decimal("0.01")

_MONTH_NAMES = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)
_MONTH_SHORT_NAMES = (
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass(frozen=True, order=True)
class YearMonth:
    """A calendar month, used for navigation and grouping."""

    year: int
    month: int

    def __post_init__(self) -> None:
        year_is_valid = date.min.year <= self.year <= date.max.year
        if not year_is_valid or not 1 <= self.month <= 12:
            raise ValidationError("Месяц выходит за пределы допустимого диапазона.")

    @classmethod
    def today(cls) -> YearMonth:
        return cls.of(date.today())

    @classmethod
    def of(cls, day: date) -> YearMonth:
        return cls(day.year, day.month)

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def label(self) -> str:
        return f"{_MONTH_NAMES[self.month - 1]} {self.year}"

    @property
    def short_label(self) -> str:
        return _MONTH_SHORT_NAMES[self.month - 1]

    def shifted(self, months: int) -> YearMonth:
        month_index = self.year * 12 + (self.month - 1) + months
        year, zero_based_month = divmod(month_index, 12)
        return YearMonth(year, zero_based_month + 1)


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    kind: TransactionType
    color: str


@dataclass(frozen=True)
class NewTransaction:
    """A transaction that has been validated but not stored yet."""

    kind: TransactionType
    amount: Decimal
    category_id: int
    occurred_on: date
    note: str


@dataclass(frozen=True)
class Transaction:
    id: int
    kind: TransactionType
    amount: Decimal
    category: Category
    occurred_on: date
    note: str


@dataclass(frozen=True)
class MonthSummary:
    income: Decimal
    expense: Decimal

    @property
    def balance(self) -> Decimal:
        return self.income - self.expense

    @property
    def savings_rate(self) -> Decimal | None:
        """Share of income that was saved; None when there is no income."""
        if self.income == 0:
            return None
        return self.balance / self.income


@dataclass(frozen=True)
class CategoryTotal:
    category: Category
    total: Decimal


@dataclass(frozen=True)
class MonthlyPoint:
    month: YearMonth
    income: Decimal
    expense: Decimal
