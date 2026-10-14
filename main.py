"""Entry point: wires the layers together and starts the UI."""

import logging
import tkinter
from tkinter import messagebox

from financeflow.config import APP_DIRECTORY, APP_NAME, DATABASE_PATH, LOG_PATH
from financeflow.data.database import Database
from financeflow.data.sqlite_repository import (
    SqliteCategoryRepository,
    SqliteTransactionRepository,
)
from financeflow.domain.errors import FinanceFlowError
from financeflow.services.analytics_service import AnalyticsService
from financeflow.services.category_service import CategoryService
from financeflow.services.transaction_service import TransactionService
from financeflow.ui import theme
from financeflow.ui.app import FinanceFlowApp

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        APP_DIRECTORY.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))
    except OSError:
        # Console-only logging is an acceptable fallback; Database.initialize()
        # will report the underlying filesystem problem to the user.
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def show_fatal_error(message: str) -> None:
    root = tkinter.Tk()
    root.withdraw()
    messagebox.showerror(APP_NAME, message)
    root.destroy()


def main() -> None:
    configure_logging()
    database = Database(DATABASE_PATH)

    try:
        database.initialize()
        category_repository = SqliteCategoryRepository(database.connection)
        transaction_repository = SqliteTransactionRepository(database.connection)

        category_service = CategoryService(category_repository)
        category_service.ensure_defaults()
        transaction_service = TransactionService(transaction_repository, category_repository)
        analytics_service = AnalyticsService(transaction_repository)
    except FinanceFlowError as error:
        logger.exception("Application failed to start")
        show_fatal_error(f"Не удалось запустить приложение.\n\n{error}")
        return

    theme.apply_global_theme()
    app = FinanceFlowApp(transaction_service, category_service, analytics_service)
    try:
        app.mainloop()
    finally:
        database.close()


if __name__ == "__main__":
    main()
