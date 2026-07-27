"""Compatibility helpers for aggregating scan results."""

from __future__ import annotations

from backend.models.scan import ScanReport
from backend.reports.generator import ReportGenerator


def aggregate_report(report: ScanReport) -> dict[str, object]:
	return ReportGenerator().to_dict(report)


def aggregate_report_text(report: ScanReport) -> str:
	return ReportGenerator().to_text(report)
