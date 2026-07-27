"""High-level backend service for scanning removable media."""

from __future__ import annotations

from pathlib import Path
import time

from backend.database.connection import SQLiteConnectionFactory
from backend.database.malware_repository import MalwareHashRepository
from backend.models.scan import DeviceInfo, ScanReport
from backend.reports.generator import ReportGenerator
from backend.scanner.file_scanner import FileScanner


class ScanService:
    """Coordinate database-backed scanning and report generation."""

    def __init__(self, database: SQLiteConnectionFactory) -> None:
        self.database = database
        self.repository = MalwareHashRepository(database)
        self.repository.seed()
        self.scanner = FileScanner(self.repository)
        self.report_generator = ReportGenerator()

    def scan_mount_path(self, mount_path: str, device: DeviceInfo | None = None) -> ScanReport:
        return self.scanner.scan_mount_path(mount_path, device=device)

    def format_text_report(self, report: ScanReport) -> str:
        return self.report_generator.to_text(report)

    def format_json_report(self, report: ScanReport, indent: int = 2) -> str:
        return self.report_generator.to_json(report, indent=indent)

    @staticmethod
    def find_mount_point(device_node: str) -> str | None:
        try:
            with Path("/proc/mounts").open("r", encoding="utf-8") as mount_file:
                for line in mount_file:
                    parts = line.split()
                    if parts and parts[0] == device_node:
                        return parts[1].replace("\\040", " ")
        except OSError:
            return None
        return None

    def wait_for_mount(self, device_node: str, timeout: int = 15, interval: float = 1.0) -> str | None:
        for _ in range(timeout):
            time.sleep(interval)
            mount_path = self.find_mount_point(device_node)
            if mount_path and Path(mount_path).exists():
                return mount_path
        return None