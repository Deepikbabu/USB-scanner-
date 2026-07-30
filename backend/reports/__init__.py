"""Authoritative report, incident, and evidence contracts."""

from backend.reports.generator import ReportGenerator
from backend.reports.incident import incident_id, normalize_verdict

__all__ = ["ReportGenerator", "incident_id", "normalize_verdict"]
