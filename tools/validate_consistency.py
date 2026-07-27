"""Validate finalized incident JSON identity and verdict consistency."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def validate(path: str, incident_id: str, verdict: str) -> tuple[bool, str]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)
    device = payload.get("device") if isinstance(payload.get("device"), dict) else {}
    actual_id = payload.get("incident_id") or device.get("incident_id")
    actual_verdict = str(payload.get("verdict", "")).upper()
    if str(actual_id) != str(incident_id):
        return False, "incident ID mismatch"
    if actual_verdict != str(verdict).upper():
        return False, "verdict mismatch"
    if not isinstance(payload.get("risk_breakdown", {}), dict):
        return False, "risk breakdown is not an object"
    return True, "consistent"


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: validate_consistency.py REPORT INCIDENT_ID VERDICT")
    ok, message = validate(sys.argv[1], sys.argv[2], sys.argv[3])
    print(message)
    raise SystemExit(0 if ok else 1)
