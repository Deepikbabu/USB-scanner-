"""Compatibility wrapper around the backend USB monitor."""

from __future__ import annotations

from config.settings import AppSettings
from backend.database.connection import SQLiteConnectionFactory
from backend.services.container import ServiceContainer
from backend.scanner.usb_monitor import main as backend_main
from backend.scanner.usb_monitor import monitor_usb as backend_monitor_usb


def monitor_usb() -> None:
    settings = AppSettings()
    services = ServiceContainer(SQLiteConnectionFactory(settings.database_path))
    backend_monitor_usb(services.scan_service)


def main() -> int:
    settings = AppSettings()
    services = ServiceContainer(SQLiteConnectionFactory(settings.database_path))
    return backend_main(services.scan_service)


if __name__ == "__main__":
    raise SystemExit(main())
