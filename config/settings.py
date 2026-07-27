"""Runtime settings for the USB scanner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Central settings shared by backend services."""

    database_path: Path = PROJECT_ROOT / "malware_hashes.db"
