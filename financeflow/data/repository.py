"""Repository interfaces. Services depend on these, never on SQLite directly."""

from abc import ABC, abstractmethod
from datetime import date

from financeflow.domain.entities import Category, NewTransaction, Transaction, TransactionType


class CategoryRepository(ABC):
    @abstractmethod
    def add(self, name: str, kind: TransactionType, color: str) -> Category:
        """Store a new category and return it with its generated id."""

    @abstractmethod
    def get(self, category_id: int) -> Category | None:
        """Return the category or None if it does not exist."""

    @abstractmethod
    def list_by_kind(self, kind: TransactionType) -> list[Category]:
        """Return categories of the given kind in creation order."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of categories."""


class TransactionRepository(ABC):
    @abstractmethod
    def add(self, new_transaction: NewTransaction) -> Transaction:
        """Store a transaction and return it with its generated id."""

    @abstractmethod
    def delete(self, transaction_id: int) -> None:
        """Delete a transaction; raise NotFoundError if it does not exist."""

    @abstractmethod
    def list_in_range(self, date_from: date, date_to_exclusive: date) -> list[Transaction]:
        """Return transactions with date_from <= date < date_to_exclusive, newest first."""
