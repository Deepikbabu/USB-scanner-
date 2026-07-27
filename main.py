"""Backend entrypoint for the USB scanner."""

from __future__ import annotations

from config.settings import AppSettings
from backend.database.connection import SQLiteConnectionFactory
from backend.services.container import ServiceContainer
from backend.scanner.usb_monitor import monitor_usb


def main() -> int:
	settings = AppSettings()
	services = ServiceContainer(SQLiteConnectionFactory(settings.database_path))
	monitor_usb(services.scan_service)
	return 0

if __name__ == "__main__":
	raise SystemExit(main())
