"""Scan domain models used by the backend layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class DeviceInfo:
    """Metadata for a connected storage device."""

    vendor: str
    model: str
    serial: str
    node: str
    bus: str = "usb"


@dataclass(slots=True)
class FileFinding:
    """A single file-level scan result."""

    path: str
    size: int
    reason: str
    category: str
    score_delta: int


@dataclass(slots=True)
class ScanSummary:
    """Aggregate numbers for a completed scan."""

    total_files: int = 0
    risk_score: int = 0
    structural_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScanReport:
    """Full scan result for a mounted device."""

    mount_path: str
    started_at: datetime
    finished_at: datetime
    summary: ScanSummary
    high_risk: list[FileFinding] = field(default_factory=list)
    medium_risk: list[FileFinding] = field(default_factory=list)
    low_risk: list[FileFinding] = field(default_factory=list)
    device: DeviceInfo | None = None

    @property
    def threat_level(self) -> str:
        if self.summary.risk_score >= 10:
            return "HIGH"
        if self.summary.risk_score >= 5:
            return "MEDIUM"
        if self.summary.risk_score > 0:
            return "LOW"
        return "CLEAN"

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.finished_at - self.started_at).total_seconds())