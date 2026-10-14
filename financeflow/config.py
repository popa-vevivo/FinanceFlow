"""Application-wide constants."""

from pathlib import Path

APP_NAME = "FinanceFlow"

APP_DIRECTORY = Path.home() / ".financeflow"
DATABASE_PATH = APP_DIRECTORY / "financeflow.db"
LOG_PATH = APP_DIRECTORY / "financeflow.log"

CURRENCY_SYMBOL = "сум"
TREND_MONTHS = 6
MAX_NOTE_LENGTH = 200
