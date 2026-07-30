"""Machine-readable incident evidence builder."""

from __future__ import annotations

from backend.reports.incident import normalize_verdict


def build_evidence(*, incident_id, device, verdict, risk_breakdown=None,
                   findings=None, scan_coverage=None, fingerprints=None,
                   quarantine=None, timing=None, recommendations=None):
    device_payload = dict(device or {})
    device_payload["incident_id"] = incident_id
    return {
        "schema_version": 2,
        "incident_id": incident_id,
        "device": device_payload,
        "verdict": normalize_verdict(verdict),
        "risk_breakdown": dict(risk_breakdown or {}),
        "findings": list(findings or []),
        "scan_coverage": dict(scan_coverage or {}),
        "fingerprints": dict(fingerprints or {}),
        "quarantine": list(quarantine or []),
        "timing": dict(timing or {}),
        "recommendations": list(recommendations or []),
    }
