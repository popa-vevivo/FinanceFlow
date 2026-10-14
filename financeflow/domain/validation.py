"""Parsing and validation of raw user input."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from financeflow.config import MAX_NOTE_LENGTH
from financeflow.domain.entities import MONEY_QUANTUM
from financeflow.domain.errors import ValidationError

DATE_FORMAT = "%d.%m.%Y"
MAX_AMOUNT = Decimal("1000000000")

_AMOUNT_HINT = "Сумма должна быть числом, например 1500 или 1500.50."


def parse_amount(raw_value: str) -> Decimal:
    cleaned = raw_value.strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if not cleaned:
        raise ValidationError("Введите сумму.")

    try:
        amount = Decimal(cleaned)
    except InvalidOperation as error:
        raise ValidationError(_AMOUNT_HINT) from error

    if not amount.is_finite():
        raise ValidationError(_AMOUNT_HINT)
    if amount <= 0:
        raise ValidationError("Сумма должна быть больше нуля.")
    if amount > MAX_AMOUNT:
        raise ValidationError(f"Сумма не может превышать {MAX_AMOUNT:,.0f}.".replace(",", " "))

    rounded_amount = amount.quantize(MONEY_QUANTUM)
    if rounded_amount != amount:
        raise ValidationError("Сумма может содержать не более двух знаков после запятой.")
    return rounded_amount


def parse_date(raw_value: str) -> date:
    try:
        return datetime.strptime(raw_value.strip(), DATE_FORMAT).date()
    except ValueError as error:
        raise ValidationError(
            "Дата должна быть в формате ДД.ММ.ГГГГ, например 31.12.2025."
        ) from error


def validate_note(raw_value: str) -> str:
    note = raw_value.strip()
    if len(note) > MAX_NOTE_LENGTH:
        raise ValidationError(f"Заметка слишком длинная: максимум {MAX_NOTE_LENGTH} символов.")
    return note
