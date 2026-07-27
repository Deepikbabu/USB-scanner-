"""Application dependency context."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.database.connection import SQLiteConnectionFactory
from backend.services.container import ServiceContainer
from config.settings import AppSettings


@dataclass(slots=True)
class AppContext:
    """Own the settings and shared services used by an application process."""

    settings: AppSettings = field(default_factory=AppSettings)
    database: SQLiteConnectionFactory = field(init=False)
    services: ServiceContainer = field(init=False)

    def __post_init__(self) -> None:
        self.database = SQLiteConnectionFactory(self.settings.database_path)
        self.services = ServiceContainer(self.database)

    @property
    def scan_service(self):
        """Expose the configured scan service for entry points."""
        return self.services.scan_service
