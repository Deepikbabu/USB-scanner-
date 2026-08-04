"""Policy for devices exposing both storage and HID capabilities."""
from __future__ import annotations

def evaluate(capabilities: set[str] | list[str], *, typed_confirmation: str = "",
             challenge: str = "") -> dict[str, object]:
    values = {str(item).lower() for item in capabilities}
    composite = "hid" in values and "storage" in values
    if not composite:
        return {"composite": False, "minimum_verdict": None, "hid_allowed": True,
                "storage_scan_allowed": "storage" in values}
    approved = bool(challenge and typed_confirmation == challenge)
    return {"composite": True, "minimum_verdict": "SUSPICIOUS",
            "hid_allowed": approved, "storage_scan_allowed": True,
            "requires_typed_confirmation": True}
