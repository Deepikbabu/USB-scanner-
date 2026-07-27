"""Compatibility helpers for report formatting."""

from __future__ import annotations

from backend.models.scan import ScanReport
from backend.reports.generator import ReportGenerator


_generator = ReportGenerator()


def format_text_report(report: ScanReport) -> str:
	return _generator.to_text(report)


def format_json_report(report: ScanReport, indent: int = 2) -> str:
	return _generator.to_json(report, indent=indent)
