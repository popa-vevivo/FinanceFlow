"""SQLite implementations of the repository interfaces."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from financeflow.data.repository import CategoryRepository, TransactionRepository
from financeflow.domain.entities import (
    MONEY_QUANTUM,
    Category,
    NewTransaction,
    Transaction,
    TransactionType,
)
from financeflow.domain.errors import NotFoundError, RepositoryError

_MINOR_UNITS_PER_MAJOR = 100

_TRANSACTION_SELECT = """
SELECT t.id, t.kind, t.amount_minor, t.occurred_on, t.note,
       c.id AS category_id, c.name AS category_name,
       c.kind AS category_kind, c.color AS category_color
FROM transactions AS t
JOIN categories AS c ON c.id = t.category_id
"""


@contextmanager
def _translate_db_errors(action: str) -> Iterator[None]:
    """Convert low-level storage errors into user-readable RepositoryError."""
    try:
        yield
    except (sqlite3.Error, ValueError) as error:
        raise RepositoryError(f"Не удалось {action}: ошибка базы данных ({error}).") from error


def _to_minor_units(amount: Decimal) -> int:
    return int((amount * _MINOR_UNITS_PER_MAJOR).to_integral_value())


def _from_minor_units(minor_units: int) -> Decimal:
    return (Decimal(minor_units) / _MINOR_UNITS_PER_MAJOR).quantize(MONEY_QUANTUM)


def _row_to_category(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        kind=TransactionType(row["kind"]),
        color=row["color"],
    )


def _row_to_transaction(row: sqlite3.Row) -> Transaction:
    category = Category(
        id=row["category_id"],
        name=row["category_name"],
        kind=TransactionType(row["category_kind"]),
        color=row["category_color"],
    )
    return Transaction(
        id=row["id"],
        kind=TransactionType(row["kind"]),
        amount=_from_minor_units(row["amount_minor"]),
        category=category,
        occurred_on=date.fromisoformat(row["occurred_on"]),
        note=row["note"],
    )


class SqliteCategoryRepository(CategoryRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, name: str, kind: TransactionType, color: str) -> Category:
        with _translate_db_errors("сохранить категорию"):
            with self._connection:
                cursor = self._connection.execute(
                    "INSERT INTO categories (name, kind, color) VALUES (?, ?, ?)",
                    (name, kind.value, color),
                )
            return Category(id=cursor.lastrowid, name=name, kind=kind, color=color)

    def get(self, category_id: int) -> Category | None:
        with _translate_db_errors("загрузить категорию"):
            row = self._connection.execute(
                "SELECT id, name, kind, color FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()
            return _row_to_category(row) if row is not None else None

    def list_by_kind(self, kind: TransactionType) -> list[Category]:
        with _translate_db_errors("загрузить категории"):
            rows = self._connection.execute(
                "SELECT id, name, kind, color FROM categories WHERE kind = ? ORDER BY id",
                (kind.value,),
            ).fetchall()
            return [_row_to_category(row) for row in rows]

    def count(self) -> int:
        with _translate_db_errors("посчитать категории"):
            row = self._connection.execute("SELECT COUNT(*) AS total FROM categories").fetchone()
            return int(row["total"])


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, new_transaction: NewTransaction) -> Transaction:
        with _translate_db_errors("сохранить операцию"):
            with self._connection:
                cursor = self._connection.execute(
                    "INSERT INTO transactions (kind, amount_minor, category_id, occurred_on, note)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (
                        new_transaction.kind.value,
                        _to_minor_units(new_transaction.amount),
                        new_transaction.category_id,
                        new_transaction.occurred_on.isoformat(),
                        new_transaction.note,
                    ),
                )
            return self._get_by_id(cursor.lastrowid)

    def delete(self, transaction_id: int) -> None:
        with _translate_db_errors("удалить операцию"):
            with self._connection:
                cursor = self._connection.execute(
                    "DELETE FROM transactions WHERE id = ?", (transaction_id,)
                )
            if cursor.rowcount == 0:
                raise NotFoundError("Операция не найдена: возможно, она уже удалена.")

    def list_in_range(self, date_from: date, date_to_exclusive: date) -> list[Transaction]:
        with _translate_db_errors("загрузить операции"):
            rows = self._connection.execute(
                _TRANSACTION_SELECT
                + " WHERE t.occurred_on >= ? AND t.occurred_on < ?"
                + " ORDER BY t.occurred_on DESC, t.id DESC",
                (date_from.isoformat(), date_to_exclusive.isoformat()),
            ).fetchall()
            return [_row_to_transaction(row) for row in rows]

    def _get_by_id(self, transaction_id: int) -> Transaction:
        row = self._connection.execute(
            _TRANSACTION_SELECT + " WHERE t.id = ?", (transaction_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("Операция не найдена.")
        return _row_to_transaction(row)
