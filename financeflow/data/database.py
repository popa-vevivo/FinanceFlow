"""SQLite connection lifecycle and schema creation."""

import sqlite3
from pathlib import Path

from financeflow.domain.errors import RepositoryError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    kind  TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
    color TEXT NOT NULL,
    UNIQUE (name, kind)
);

CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    category_id  INTEGER NOT NULL REFERENCES categories (id),
    occurred_on  TEXT NOT NULL,
    note         TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_transactions_occurred_on
    ON transactions (occurred_on);
"""


class Database:
    """Owns the single SQLite connection used by the application."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RepositoryError("База данных не инициализирована.")
        return self._connection

    def initialize(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self._path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                connection.executescript(_SCHEMA)
        except (OSError, sqlite3.Error) as error:
            raise RepositoryError(
                f"Не удалось открыть базу данных ({self._path}): {error}"
            ) from error
        self._connection = connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
