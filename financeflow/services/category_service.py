"""Category use cases."""

from financeflow.data.repository import CategoryRepository
from financeflow.domain.entities import Category, TransactionType

# (name, kind, chart color)
_DEFAULT_CATEGORIES: tuple[tuple[str, TransactionType, str], ...] = (
    ("Продукты", TransactionType.EXPENSE, "#F59E0B"),
    ("Транспорт", TransactionType.EXPENSE, "#3B82F6"),
    ("Жильё", TransactionType.EXPENSE, "#8B5CF6"),
    ("Развлечения", TransactionType.EXPENSE, "#EC4899"),
    ("Здоровье", TransactionType.EXPENSE, "#10B981"),
    ("Другое", TransactionType.EXPENSE, "#6B7280"),
    ("Зарплата", TransactionType.INCOME, "#059669"),
    ("Подработка", TransactionType.INCOME, "#0EA5E9"),
    ("Другое", TransactionType.INCOME, "#6B7280"),
)


class CategoryService:
    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def ensure_defaults(self) -> None:
        """Seed the starter categories on first launch only."""
        if self._categories.count() > 0:
            return
        for name, kind, color in _DEFAULT_CATEGORIES:
            self._categories.add(name, kind, color)

    def list_for_kind(self, kind: TransactionType) -> list[Category]:
        return self._categories.list_by_kind(kind)
