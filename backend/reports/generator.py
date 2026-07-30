"""Serialization for modular backend scan reports."""

from __future__ import annotations

import json
from dataclasses import asdict

from backend.models.scan import ScanReport


class ReportGenerator:
    def to_dict(self, report: ScanReport) -> dict:
        return {
            "mount_path": report.mount_path,
            "started_at": report.started_at.isoformat(),
            "finished_at": report.finished_at.isoformat(),
            "duration_seconds": report.duration_seconds,
            "threat_level": report.threat_level,
            "summary": asdict(report.summary),
            "device": asdict(report.device) if report.device else None,
            "findings": {
                "high": [asdict(item) for item in report.high_risk],
                "medium": [asdict(item) for item in report.medium_risk],
                "low": [asdict(item) for item in report.low_risk],
            },
        }

    def to_json(self, report: ScanReport, indent: int = 2) -> str:
        return json.dumps(self.to_dict(report), indent=indent, ensure_ascii=False)

    def to_text(self, report: ScanReport) -> str:
        payload = self.to_dict(report)
        lines = [
            "USB Security Scanner Report",
            "===========================",
            f"Threat level : {payload['threat_level']}",
            f"Mount path   : {payload['mount_path']}",
            f"Files scanned: {payload['summary']['total_files']}",
            f"Risk score   : {payload['summary']['risk_score']}",
            f"Duration     : {payload['duration_seconds']:.2f}s",
        ]
        for category in ("high", "medium", "low"):
            for finding in payload["findings"][category]:
                lines.append(
                    f"[{category.upper()}] {finding['path']}: {finding['reason']} "
                    f"(+{finding['score_delta']})"
                )
        return "\n".join(lines)
