"""SQLite connection helpers for backend services."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteConnectionFactory:
    """Creates SQLite connections without coupling callers to a fixed path."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.database_path)
