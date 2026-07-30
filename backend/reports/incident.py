"""Stable incident identity and verdict normalization."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

VERDICTS = {"CLEAN", "TRUSTED", "SUSPICIOUS", "DANGEROUS", "INCOMPLETE"}


def normalize_verdict(value: object) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in VERDICTS else "INCOMPLETE"


def incident_id(port: object = "") -> str:
    safe_port = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(port or "unknown")).strip("-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"inc-{stamp}-{safe_port or 'unknown'}-{secrets.token_hex(3)}"
