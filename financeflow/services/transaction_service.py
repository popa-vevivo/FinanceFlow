"""Transaction use cases: validate raw input, enforce rules, delegate storage."""

from financeflow.data.repository import CategoryRepository, TransactionRepository
from financeflow.domain.entities import NewTransaction, Transaction, TransactionType, YearMonth
from financeflow.domain.errors import ValidationError
from financeflow.domain.validation import parse_amount, parse_date, validate_note


class TransactionService:
    def __init__(
        self,
        transactions: TransactionRepository,
        categories: CategoryRepository,
    ) -> None:
        self._transactions = transactions
        self._categories = categories

    def add_transaction(
        self,
        kind: TransactionType,
        raw_amount: str,
        category_id: int,
        raw_date: str,
        raw_note: str,
    ) -> Transaction:
        amount = parse_amount(raw_amount)
        occurred_on = parse_date(raw_date)
        note = validate_note(raw_note)

        category = self._categories.get(category_id)
        if category is None:
            raise ValidationError("Выбранная категория не найдена.")
        if category.kind is not kind:
            raise ValidationError("Категория не подходит для этого типа операции.")

        return self._transactions.add(
            NewTransaction(
                kind=kind,
                amount=amount,
                category_id=category.id,
                occurred_on=occurred_on,
                note=note,
            )
        )

    def delete_transaction(self, transaction_id: int) -> None:
        self._transactions.delete(transaction_id)

    def list_for_month(self, month: YearMonth) -> list[Transaction]:
        return self._transactions.list_in_range(month.first_day, month.shifted(1).first_day)
