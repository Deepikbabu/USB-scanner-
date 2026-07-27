"""Dependency container for backend services."""

from __future__ import annotations

from dataclasses import dataclass

from backend.database.connection import SQLiteConnectionFactory
from backend.services.scan_service import ScanService


@dataclass(slots=True)
class ServiceContainer:
    """Holds backend dependencies for the scanner services."""

    database: SQLiteConnectionFactory
    scan_service: ScanService | None = None

    def __post_init__(self) -> None:
        if self.scan_service is None:
            self.scan_service = ScanService(self.database)
