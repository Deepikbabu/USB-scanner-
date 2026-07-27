"""Focused tests for the modular backend's context and reporting contract."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from backend.models.scan import DeviceInfo, FileFinding, ScanReport, ScanSummary
from backend.reports.generator import ReportGenerator
from config.settings import AppSettings
from core.context import AppContext


class ReportGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        started = datetime(2026, 1, 2, 3, 4, 5)
        self.report = ScanReport(
            mount_path="/media/test",
            started_at=started,
            finished_at=started + timedelta(seconds=1.25),
            summary=ScanSummary(
                total_files=1,
                risk_score=10,
                structural_flags=["YARA: USB_EICAR_Test"],
            ),
            high_risk=[
                FileFinding(
                    path="/media/test/eicar.com",
                    size=68,
                    reason="Malware Detected: EICAR-Test-File",
                    category="high",
                    score_delta=10,
                )
            ],
            device=DeviceInfo("Example", "Drive", "ABC123", "/dev/sdb1"),
        )

    def test_dictionary_is_json_safe_and_complete(self) -> None:
        payload = ReportGenerator().to_dict(self.report)
        self.assertEqual(payload["threat_level"], "HIGH")
        self.assertEqual(payload["duration_seconds"], 1.25)
        self.assertEqual(payload["device"]["serial"], "ABC123")
        self.assertEqual(payload["findings"]["high"][0]["score_delta"], 10)
        json.dumps(payload)

    def test_json_and_text_formats(self) -> None:
        generator = ReportGenerator()
        payload = json.loads(generator.to_json(self.report))
        text = generator.to_text(self.report)
        self.assertEqual(payload["summary"]["total_files"], 1)
        self.assertIn("Threat level : HIGH", text)
        self.assertIn("EICAR-Test-File", text)


class AppContextTests(unittest.TestCase):
    def test_context_builds_shared_services(self) -> None:
        settings = AppSettings()
        context = AppContext(settings)
        self.assertIs(context.services.database, context.database)
        self.assertIs(context.scan_service, context.services.scan_service)
        self.assertEqual(context.database.database_path, settings.database_path)


if __name__ == "__main__":
    unittest.main()
